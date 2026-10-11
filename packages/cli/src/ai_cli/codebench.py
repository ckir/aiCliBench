"""`codebench` command (§4). Local-first benchmarking of Claude vs Antigravity CLIs."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import suppress
from pathlib import Path
from typing import Annotated, Any

import typer

from ai_benchmark.config import resolve_config
from ai_benchmark.docker_runner import build_image, docker_available
from ai_benchmark.doctor import run_doctor
from ai_benchmark.export import export_csv, export_json
from ai_benchmark.reporting import render_report
from ai_benchmark.scheduler import ExperimentRequest, run_experiment
from ai_benchmark.scoring import score_experiment
from ai_benchmark.storage import (
    connect,
    evaluation_for_run,
    get_experiment,
    latest_experiment_id,
    list_experiments,
    runs_for_experiment,
)
from ai_benchmark.task_registry import discover_tasks, validate_task
from ai_core.errors import ConfigurationError

app = typer.Typer(help="CodeBench Local: compare coding-agent CLIs with isolated trials.")
tasks_app = typer.Typer(help="Task commands (list/validate, never runs agents).")
runs_app = typer.Typer(help="Run history commands.")
app.add_typer(tasks_app, name="tasks")
app.add_typer(runs_app, name="runs")

EXIT_CONFIG = 2
EXIT_TASK = 3
EXIT_DEPENDENCY = 4
EXIT_INTERRUPTED = 130


def _default_config_path() -> Path | None:
    candidate = Path("config/benchmark.toml")
    return candidate if candidate.is_file() else None


def _load_config(config: Path | None) -> Any:
    path = config or _default_config_path()
    try:
        return resolve_config(path, None)
    except ConfigurationError as exc:
        typer.echo(f"Invalid config: {exc}", err=True)
        raise typer.Exit(code=EXIT_CONFIG) from exc


def _tasks_root() -> Path:
    tasks_root = os.environ.get("TASKS_ROOT")
    if tasks_root:
        return Path(tasks_root)
    return Path("tasks")


def _resolve_agents(selection: str, cfg: Any) -> dict[str, Any]:
    from ai_integration_antigravity.adapter import AntigravityAdapter
    from ai_integration_antigravity.config import AntigravityConfig
    from ai_integration_claude_code.adapter import ClaudeCodeAdapter
    from ai_integration_claude_code.config import ClaudeCodeConfig

    wanted: list[str]
    if selection == "all":
        wanted = ["claude", "antigravity"]
    elif selection in ("claude", "antigravity"):
        wanted = [selection]
    else:
        typer.echo(f"Unknown --agents {selection!r}; use all|claude|antigravity", err=True)
        raise typer.Exit(code=EXIT_CONFIG)
    adapters: dict[str, Any] = {}
    for name in wanted:
        if name == "claude":
            if not cfg.agents.claude.enabled:
                continue
            adapters[name] = ClaudeCodeAdapter(
                ClaudeCodeConfig(
                    command=cfg.agents.claude.command,
                    model=cfg.agents.claude.model,
                    timeout_seconds=float(cfg.agents.claude.timeout_seconds),
                    output_format=cfg.agents.claude.output_format or "json",
                )
            )
        else:
            if not cfg.agents.antigravity.enabled:
                continue
            adapters[name] = AntigravityAdapter(
                AntigravityConfig(
                    command=cfg.agents.antigravity.command,
                    model=cfg.agents.antigravity.model,
                    timeout_seconds=float(cfg.agents.antigravity.timeout_seconds),
                    output_format=cfg.agents.antigravity.output_format or "stream-json",
                )
            )
    if not adapters:
        typer.echo("No requested agents are enabled/available.", err=True)
        raise typer.Exit(code=EXIT_DEPENDENCY)
    return adapters


def _open_db(cfg: Any) -> sqlite3.Connection:
    try:
        return connect(Path(cfg.data.database))
    except Exception as exc:
        typer.echo(f"Cannot open database: {exc}", err=True)
        raise typer.Exit(code=EXIT_CONFIG) from exc


def _select_experiment(
    conn: sqlite3.Connection, experiment: str | None, latest: bool
) -> dict[str, Any]:
    exp_id = experiment
    if exp_id is None and latest:
        exp_id = latest_experiment_id(conn)
    if exp_id is None:
        typer.echo("Specify --experiment ID or --latest.", err=True)
        raise typer.Exit(code=EXIT_CONFIG)
    record = get_experiment(conn, exp_id)
    if record is None:
        typer.echo(f"Experiment not found: {exp_id}", err=True)
        raise typer.Exit(code=EXIT_TASK)
    return record


@app.command()
def doctor(
    config: Annotated[Path | None, typer.Option(help="Path to benchmark.toml")] = None,
) -> None:
    """Check environment without paid or state-changing tasks (§4.1)."""
    cfg = _load_config(config)
    report = run_doctor(
        config_path=config or _default_config_path(),
        data_dir=Path(cfg.data.directory),
        claude_command=cfg.agents.claude.command,
        agy_command=cfg.agents.antigravity.command,
    )
    for check in report.checks:
        mark = "ok" if check.ok else "FAIL"
        typer.echo(f"[{mark}] {check.name}: {check.detail}")
    if not report.ok:
        raise typer.Exit(code=EXIT_DEPENDENCY)


@tasks_app.command("list")
def tasks_list(
    suite: Annotated[str | None, typer.Option(help="Suite name")] = None,
) -> None:
    """Print task ID, title, category, repository, validation state."""
    root = _tasks_root()
    try:
        tasks = discover_tasks(root, suite=suite)
    except ConfigurationError as exc:
        typer.echo(f"Cannot list tasks: {exc}", err=True)
        raise typer.Exit(code=EXIT_TASK) from exc
    for loaded in tasks:
        validation = validate_task(loaded.task_dir, check_repo=False)
        state = "valid" if validation.ok else "invalid"
        typer.echo(
            f"{loaded.definition.id}\t{loaded.definition.title}\t"
            f"{loaded.definition.category}\t{loaded.definition.repository}\t{state}"
        )


@tasks_app.command("validate")
def tasks_validate(
    task_id: Annotated[str | None, typer.Argument(help="Task ID (default: all)")] = None,
    suite: Annotated[str | None, typer.Option(help="Suite name")] = None,
) -> None:
    """Validate task metadata without running an agent (§4.2, §11.3)."""
    root = _tasks_root()
    try:
        tasks = discover_tasks(root, suite=suite)
    except ConfigurationError as exc:
        typer.echo(f"Cannot load tasks: {exc}", err=True)
        raise typer.Exit(code=EXIT_TASK) from exc
    selected = [t for t in tasks if task_id is None or t.definition.id == task_id]
    if task_id is not None and not selected:
        typer.echo(f"Task not found: {task_id}", err=True)
        raise typer.Exit(code=EXIT_TASK)
    failed = False
    for loaded in selected:
        result = validate_task(loaded.task_dir, check_repo=True)
        status = "VALID" if result.ok else "INVALID"
        typer.echo(f"{loaded.definition.id}: {status}")
        for error in result.errors:
            typer.echo(f"  error: {error}", err=True)
        for warning in result.warnings:
            typer.echo(f"  warning: {warning}")
        failed = failed or not result.ok
    if failed:
        raise typer.Exit(code=EXIT_TASK)


@tasks_app.command("build")
def tasks_build(
    suite: Annotated[str | None, typer.Option(help="Suite name")] = None,
    all: Annotated[bool, typer.Option(help="Build all suites")] = False,
    config: Annotated[Path | None, typer.Option(help="Path to benchmark.toml")] = None,
) -> None:
    """Pre-build Docker images for all tasks in a suite (§5)."""
    if not all and suite is None:
        typer.echo("Specify --suite SUITE or --all.", err=True)
        raise typer.Exit(code=EXIT_CONFIG)
    if not docker_available():
        typer.echo("Docker not available; cannot build images.", err=True)
        raise typer.Exit(code=EXIT_DEPENDENCY)

    _load_config(config)
    root = _tasks_root()

    suites: list[str]
    if all:
        suites = [p.name for p in root.iterdir() if p.is_dir()] if root.is_dir() else []
    else:
        if suite is None:
            typer.echo("Specify --suite SUITE or --all.", err=True)
            raise typer.Exit(code=EXIT_CONFIG)
        suites = [suite]

    if not suites:
        typer.echo("No suites found.", err=True)
        raise typer.Exit(code=EXIT_TASK)

    typer.echo(f"Building images for suites: {', '.join(suites)}")
    built_count = 0
    skipped_count = 0

    for suite_name in suites:
        suite_dir = root / suite_name
        if not suite_dir.is_dir():
            typer.echo(f"Suite not found: {suite_name}", err=True)
            continue

        try:
            tasks = discover_tasks(root, suite=suite_name)
        except ConfigurationError as exc:
            typer.echo(f"Cannot load suite {suite_name}: {exc}", err=True)
            continue

        for loaded in tasks:
            task = loaded.definition
            dockerfile_path = (loaded.task_dir / task.dockerfile).resolve()
            if not dockerfile_path.is_file():
                typer.echo(f"  {task.id}: SKIP (missing Dockerfile)")
                skipped_count += 1
                continue

            typer.echo(f"  Building {task.id}...")
            try:
                image_tag = f"codebench-task:{task.id}"
                build_image(
                    dockerfile=dockerfile_path,
                    context=loaded.task_dir.resolve(),
                    tag=image_tag,
                )
                typer.echo(f"  {task.id}: BUILT ({image_tag})")
                built_count += 1
            except Exception as exc:
                typer.echo(f"  {task.id}: FAILED ({exc})", err=True)

    typer.echo(f"Build complete: {built_count} built, {skipped_count} skipped.")


@app.command()
def run(
    task: Annotated[str | None, typer.Option(help="Single task ID")] = None,
    suite: Annotated[str | None, typer.Option(help="Suite name")] = None,
    agents: Annotated[str, typer.Option(help="all|claude|antigravity")] = "all",
    repeat: Annotated[int, typer.Option(help="Repetitions per agent (positive int)")] = 1,
    config: Annotated[Path | None, typer.Option(help="Path to benchmark.toml")] = None,
    notes: Annotated[str, typer.Option(help="Experiment notes")] = "",
) -> None:
    """Run paired trials with fresh workspaces (§4.3, §10). Sequential, no auto-retry."""
    if repeat < 1:
        typer.echo("--repeat must be a positive integer", err=True)
        raise typer.Exit(code=EXIT_CONFIG)
    if task is None and suite is None:
        typer.echo("Specify --task TASK_ID or --suite SUITE.", err=True)
        raise typer.Exit(code=EXIT_CONFIG)
    cfg = _load_config(config)
    root = _tasks_root()
    effective_suite = suite
    task_ids: list[str]
    if task is not None:
        # Locate the task's suite.
        task_ids = [task]
        if effective_suite is None:
            found = None
            for suite_dir in root.iterdir() if root.is_dir() else []:
                if not suite_dir.is_dir():
                    continue
                for candidate in suite_dir.glob("*/task.toml"):
                    from ai_benchmark.task_registry import load_task as _load

                    with suppress(Exception):
                        loaded = _load(candidate.parent)
                        if loaded.definition.id == task:
                            found = loaded.definition.suite
                            break
            if found is None:
                typer.echo(f"Task not found: {task}", err=True)
                raise typer.Exit(code=EXIT_TASK)
            effective_suite = found
    else:
        if suite is None:  # defensive; guarded by task/suite check above
            typer.echo("Specify --task TASK_ID or --suite SUITE.", err=True)
            raise typer.Exit(code=EXIT_CONFIG)
        effective_suite = suite
        try:
            task_ids = [t.definition.id for t in discover_tasks(root, suite=suite)]
        except ConfigurationError as exc:
            typer.echo(f"Cannot load suite: {exc}", err=True)
            raise typer.Exit(code=EXIT_TASK) from exc
    adapters = _resolve_agents(agents, cfg)
    typer.echo(
        f"Starting experiment: suite={effective_suite} tasks={len(task_ids)} "
        f"agents={sorted(adapters)} repeat={repeat} (sequential, no auto-retry)"
    )
    try:
        summary = run_experiment(
            config=cfg,
            tasks_root=root,
            request=ExperimentRequest(
                suite=effective_suite,
                task_ids=task_ids,
                agent_names=sorted(adapters),
                repeat_count=repeat,
                notes=notes,
            ),
            adapters=adapters,
            db_path=Path(cfg.data.database),
            runs_dir=Path(cfg.data.directory),
        )
    except KeyboardInterrupt:
        typer.echo("Interrupted: active execution terminated, partial results saved.", err=True)
        raise typer.Exit(code=EXIT_INTERRUPTED) from None
    except ConfigurationError as exc:
        typer.echo(f"Run failed: {exc}", err=True)
        raise typer.Exit(code=EXIT_TASK) from exc
    typer.echo(
        f"Experiment {summary.experiment_id} {summary.status}: "
        f"{summary.completed}/{summary.total_runs} runs completed."
    )
    if summary.status != "completed":
        typer.echo("Warning: incomplete experiment; headline scores exclude missing pairs.")


@runs_app.command("list")
def runs_list(
    limit: Annotated[int, typer.Option(help="Max experiments to show")] = 10,
    config: Annotated[Path | None, typer.Option(help="Path to benchmark.toml")] = None,
) -> None:
    """List recent experiments."""
    cfg = _load_config(config)
    conn = _open_db(cfg)
    for row in list_experiments(conn, limit=limit):
        typer.echo(f"{row['id']}\t{row['status']}\t{row['suite']}\t{row['created_at']}")
    conn.close()


@runs_app.command("clean")
def runs_clean(
    dry_run: Annotated[bool, typer.Option(help="Show what would be removed")] = True,
    confirm: Annotated[bool, typer.Option(help="Actually remove retained workspaces")] = False,
    config: Annotated[Path | None, typer.Option(help="Path to benchmark.toml")] = None,
) -> None:
    """Remove retained workspaces (safeguarded; never deletes source repos)."""
    cfg = _load_config(config)
    base = Path(cfg.data.directory)
    workspaces = sorted(base.glob("*/*/workspace"))
    if dry_run or not confirm:
        typer.echo(f"Would remove {len(workspaces)} workspace directories under {base}.")
        for path in workspaces[:20]:
            typer.echo(f"  {path}")
        if not confirm:
            typer.echo("Pass --confirm --no-dry-run to actually remove.")
        return
    import shutil as _shutil

    removed = 0
    for path in workspaces:
        # Safety: only under the data dir, never source repos or arbitrary paths.
        try:
            path.relative_to(base.resolve())
        except ValueError:
            continue
        _shutil.rmtree(path, ignore_errors=True)
        removed += 1
    typer.echo(f"Removed {removed} workspace directories.")


@app.command()
def compare(
    experiment: Annotated[str | None, typer.Option(help="Experiment ID")] = None,
    latest: Annotated[bool, typer.Option(help="Use latest experiment")] = True,
    config: Annotated[Path | None, typer.Option(help="Path to benchmark.toml")] = None,
) -> None:
    """Print correctness, paired outcomes, runtime, and cost coverage."""
    cfg = _load_config(config)
    conn = _open_db(cfg)
    record = _select_experiment(conn, experiment, latest)
    runs = runs_for_experiment(conn, record["id"])
    evaluations = [
        evaluation_for_run(conn, run["id"])
        for run in runs
        if evaluation_for_run(conn, run["id"]) is not None
    ]
    evaluations = [e for e in evaluations if e is not None]
    conn.close()
    score = score_experiment(runs, evaluations)
    for agent, summary in score.by_agent.items():
        rate = f"{summary.pass_rate:.2%}" if summary.pass_rate is not None else "n/a"
        typer.echo(
            f"{agent}: {summary.acceptance_passes}/{summary.eligible_evaluations} "
            f"pass ({rate}); timeout {summary.timeout_rate:.0%}, "
            f"agent-error {summary.agent_error_rate:.0%}"
        )
    if score.paired is not None:
        typer.echo(
            f"paired: A-wins {score.paired.a_wins}, B-wins {score.paired.b_wins}, "
            f"both {score.paired.both_pass}, neither {score.paired.neither_pass}, "
            f"invalid {score.paired.invalid}"
        )
    for agent, runtime in score.runtime_by_agent.items():
        median = runtime.median_success_seconds
        median_str = f"{median}s" if median is not None else "n/a"
        typer.echo(
            f"{agent} runtime: median "
            f"{median_str} "
            f"over {runtime.successful_count} successes; timeouts {runtime.timeout_count}"
        )
    for agent, cost in score.cost_by_agent.items():
        per_success = (
            f"{cost.cost_per_success:.4f}" if cost.cost_per_success is not None else "not available"
        )
        typer.echo(
            f"{agent} cost: {cost.total_known_cost_usd:.4f} known, "
            f"per-success {per_success} "
            f"(coverage {cost.coverage_known}/{cost.coverage_total})"
        )
    if record["status"] != "completed":
        typer.echo(f"Warning: experiment status is {record['status']}; results incomplete.")
    # Quality gate counts
    for agent, gates in score.quality_gates.items():
        build = f"{gates.get('build_pass', 0)}/{gates.get('build_total', 0)}" if gates.get('build_total', 0) else "n/a"
        lint = f"{gates.get('lint_pass', 0)}/{gates.get('lint_total', 0)}" if gates.get('lint_total', 0) else "n/a"
        typecheck = f"{gates.get('typecheck_pass', 0)}/{gates.get('typecheck_total', 0)}" if gates.get('typecheck_total', 0) else "n/a"
        typer.echo(f"{agent} gates: build {build}, lint {lint}, typecheck {typecheck}")


@app.command()
def report(
    experiment: Annotated[str | None, typer.Option(help="Experiment ID")] = None,
    latest: Annotated[bool, typer.Option(help="Use latest experiment")] = True,
    format: Annotated[str, typer.Option(help="html")] = "html",
    output: Annotated[Path | None, typer.Option(help="Output path")] = None,
    config: Annotated[Path | None, typer.Option(help="Path to benchmark.toml")] = None,
) -> None:
    """Generate a static local-only HTML report (§15)."""
    if format != "html":
        typer.echo("Only --format html is supported.", err=True)
        raise typer.Exit(code=EXIT_CONFIG)
    cfg = _load_config(config)
    conn = _open_db(cfg)
    record = _select_experiment(conn, experiment, latest)
    runs = runs_for_experiment(conn, record["id"])
    evaluations = [
        e for e in (evaluation_for_run(conn, run["id"]) for run in runs) if e is not None
    ]
    conn.close()
    score = score_experiment(runs, evaluations)
    try:
        tool_versions = json.loads(record.get("tool_versions_json", "{}") or "{}")
    except (json.JSONDecodeError, ValueError):
        tool_versions = {}
    warnings: list[str] = []
    if record["status"] != "completed":
        warnings.append(f"Experiment incomplete (status {record['status']}).")
    if score.paired is not None and score.paired.invalid:
        warnings.append(f"{score.paired.invalid} invalid pairs excluded from win rates.")
    html = render_report(
        title=str(cfg.report.title),
        experiment=record,
        runs=runs,
        evaluations=evaluations,
        score=score,
        tool_versions=tool_versions,
        warnings=warnings,
    )
    out_path = output or (Path(cfg.data.directory) / record["id"] / "report.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    typer.echo(f"Wrote {out_path}")


@app.command()
def export(
    experiment: Annotated[str | None, typer.Option(help="Experiment ID")] = None,
    latest: Annotated[bool, typer.Option(help="Use latest experiment")] = True,
    format: Annotated[str, typer.Option(help="json|csv")] = "json",
    output: Annotated[Path | None, typer.Option(help="Output path")] = None,
    config: Annotated[Path | None, typer.Option(help="Path to benchmark.toml")] = None,
) -> None:
    """Export deterministic JSON/CSV (§15)."""
    if format not in ("json", "csv"):
        typer.echo("Use --format json|csv.", err=True)
        raise typer.Exit(code=EXIT_CONFIG)
    cfg = _load_config(config)
    conn = _open_db(cfg)
    record = _select_experiment(conn, experiment, latest)
    runs = runs_for_experiment(conn, record["id"])
    evaluations = [
        e for e in (evaluation_for_run(conn, run["id"]) for run in runs) if e is not None
    ]
    conn.close()
    if format == "json":
        payload = export_json(experiment=record, runs=runs, evaluations=evaluations)
        out_path = output or (Path(cfg.data.directory) / record["id"] / "export.json")
    else:
        payload = export_csv(runs=runs, evaluations=evaluations)
        out_path = output or (Path(cfg.data.directory) / record["id"] / "export.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    typer.echo(f"Wrote {out_path}")
