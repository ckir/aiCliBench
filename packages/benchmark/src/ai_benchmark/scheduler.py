"""Paired experiment scheduler (§10). Sequential, seeded, fresh workspaces."""

from __future__ import annotations

import contextlib
import hashlib
import json
import platform
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_agents.adapter import paired_order
from ai_benchmark import storage as storage_module
from ai_benchmark.config import config_snapshot
from ai_benchmark.evaluator import GateSpec, evaluator_digest, run_evaluation
from ai_benchmark.provenance import build_manifest, environment_digest, inspect_image
from ai_benchmark.redaction import redact_text
from ai_benchmark.task_materialize import MaterializeMismatchError, materialize_repo
from ai_benchmark.task_registry import LoadedTask, load_task, resolve_repository
from ai_benchmark.workspace import checkout_fresh, workspace_diff
from ai_core.errors import ConfigurationError
from ai_core.ids import new_id
from ai_schemas import BenchmarkConfig
from ai_schemas.codebench import PROMPT_WRAPPER_VERSION


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def host_info() -> dict[str, Any]:
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
    }


def docker_version() -> str | None:
    try:
        result = subprocess.run(
            [  # noqa: S607 - intentional PATH lookup of explicit tool
                "docker",
                "--version",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr or "").strip().splitlines()[0][:200]


def _file_sha(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def _write_text(path: Path, text: str, *, redact: bool = True) -> tuple[str, int, bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    redacted_text, was_redacted = redact_text(text) if redact else (text, False)
    path.write_text(redacted_text, encoding="utf-8")
    data = redacted_text.encode("utf-8")
    return hashlib.sha256(data).hexdigest(), len(data), was_redacted


@dataclass(frozen=True, slots=True)
class ExperimentRequest:
    suite: str
    task_ids: list[str]
    agent_names: list[str]
    repeat_count: int = 1
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ExperimentSummary:
    experiment_id: str
    status: str
    total_runs: int
    completed: int
    interrupted: int


def _validate_request(
    config: BenchmarkConfig, tasks_root: Path, request: ExperimentRequest
) -> list[LoadedTask]:
    if request.repeat_count < 1:
        raise ConfigurationError("--repeat must be a positive integer")
    if not request.task_ids:
        raise ConfigurationError("no tasks selected")
    if not request.agent_names:
        raise ConfigurationError("no agents selected")
    if config.execution.parallelism != 1:
        raise ConfigurationError("MVP runs sequentially; parallelism must be 1")
    loaded: list[LoadedTask] = []
    for task_id in request.task_ids:
        # Find task dir by id under suite.
        candidates = list((tasks_root / request.suite).glob("*/task.toml"))
        match: Path | None = None
        for candidate in candidates:
            task_dir = candidate.parent
            candidate_loaded = load_task(task_dir)
            if candidate_loaded.definition.id == task_id:
                match = task_dir
                break
        if match is None:
            raise ConfigurationError(f"task not found: {task_id!r} in suite {request.suite!r}")
        loaded.append(load_task(match))
        # Task timeout vs global max.
        task = loaded[-1].definition
        if task.timeout_seconds > config.execution.global_max_timeout_seconds:
            raise ConfigurationError(
                f"task {task_id} timeout exceeds global maximum "
                f"({task.timeout_seconds} > {config.execution.global_max_timeout_seconds})"
            )
    return loaded


def run_experiment(
    *,
    config: BenchmarkConfig,
    tasks_root: Path,
    request: ExperimentRequest,
    adapters: dict[str, Any],
    db_path: Path,
    runs_dir: Path,
    experiment_id: str | None = None,
    use_docker: bool | None = None,
) -> ExperimentSummary:
    """Run a full paired experiment (§10). Sequential; no auto-retry."""
    for agent_name in request.agent_names:
        if agent_name not in adapters:
            raise ConfigurationError(
                f"agent {agent_name!r} requested but no adapter available; "
                "install/authenticate the CLI or request a partial run explicitly"
            )
    loaded_tasks = _validate_request(config, tasks_root, request)
    exp_id = experiment_id or new_id("exp")
    created_at = utc_now()
    tool_versions: dict[str, Any] = {"docker": docker_version()}
    for name, adapter in adapters.items():
        try:
            tool_versions[name] = adapter.version()
        except Exception:
            tool_versions[name] = None

    conn = storage_module.connect(db_path)

    should_docker = use_docker
    if should_docker is None:
        from ai_benchmark.docker_runner import docker_available

        should_docker = docker_available()

    # Build provenance manifest
    agents_info = {name: adapter.capability.model_dump() for name, adapter in adapters.items()}
    tasks_info = {}
    for loaded in loaded_tasks:
        task = loaded.definition
        task_dir = loaded.task_dir
        env_digest = environment_digest(task_dir, task.dockerfile)
        image = inspect_image(f"codebench-task:{task.id}") if should_docker else None
        tasks_info[task.id] = {
            "commit": task.commit,
            "instruction_sha256": loaded.instruction_sha256,
            "evaluator_digest": (
                evaluator_digest(task_dir / "evaluator")
                if (task_dir / "evaluator").is_dir()
                else ""
            ),
            "environment_digest": env_digest,
            "image_id": image.image_id if image else None,
        }
    manifest = build_manifest(
        prompt_wrapper_version=PROMPT_WRAPPER_VERSION,
        docker=docker_version(),
        agents=agents_info,
        tasks=tasks_info,
    )
    provenance_json = json.dumps(manifest, sort_keys=True)
    manifest_path = runs_dir / exp_id / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8")

    storage_module.insert_experiment(
        conn,
        {
            "id": exp_id,
            "created_at": created_at,
            "started_at": created_at,
            "ended_at": None,
            "status": "running",
            "suite": request.suite,
            "task_ids_json": json.dumps([t.definition.id for t in loaded_tasks], sort_keys=True),
            "agent_names_json": json.dumps(list(request.agent_names), sort_keys=True),
            "repeat_count": request.repeat_count,
            "random_seed": config.execution.random_seed,
            "resolved_config_json": json.dumps(config_snapshot(config), sort_keys=True),
            "host_info_json": json.dumps(host_info(), sort_keys=True),
            "tool_versions_json": json.dumps(tool_versions, sort_keys=True, default=str),
            "notes": request.notes,
            "provenance_json": provenance_json,
        },
    )
    conn.commit()

    total = 0
    completed = 0
    interrupted_count = 0
    exp_status = "completed"
    try:
        for loaded in loaded_tasks:
            task = loaded.definition
            for repetition in range(1, request.repeat_count + 1):
                pair_key = f"{task.id}:{repetition}"
                order = paired_order(
                    list(request.agent_names),
                    seed=config.execution.random_seed,
                    pair_key=pair_key,
                )
                for order_index, agent_name in enumerate(order):
                    total += 1
                    run_id = new_id("run")
                    artifact_dir = runs_dir / exp_id / run_id
                    artifact_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        _run_once(
                            config=config,
                            loaded=loaded,
                            adapter=adapters[agent_name],
                            conn=conn,
                            exp_id=exp_id,
                            run_id=run_id,
                            repetition=repetition,
                            pair_key=pair_key,
                            order_index=order_index,
                            artifact_dir=artifact_dir,
                            use_docker=bool(should_docker),
                        )
                        completed += 1
                    except KeyboardInterrupt:
                        interrupted_count += 1
                        exp_status = "interrupted"
                        _mark_run_interrupted(conn, run_id)
                        conn.commit()
                        raise
                    except Exception:
                        # Preserve the failure as a recorded run where possible;
                        # scheduler-level crashes still mark partial.
                        exp_status = "completed_partial"
                        continue
    except KeyboardInterrupt:
        storage_module.update_experiment_status(
            conn, exp_id, status="interrupted", ended_at=utc_now()
        )
        conn.commit()
        conn.close()
        raise
    if interrupted_count:
        exp_status = "interrupted"
    elif completed < total:
        exp_status = "completed_partial" if completed else "failed"
    storage_module.update_experiment_status(conn, exp_id, status=exp_status, ended_at=utc_now())
    conn.commit()
    conn.close()
    return ExperimentSummary(
        experiment_id=exp_id,
        status=exp_status,
        total_runs=total,
        completed=completed,
        interrupted=interrupted_count,
    )


def _mark_run_interrupted(conn: sqlite3.Connection, run_id: str) -> None:
    with contextlib.suppress(Exception):
        storage_module.update_run(conn, run_id, {"status": "interrupted", "ended_at": utc_now()})


def _run_once(
    *,
    config: BenchmarkConfig,
    loaded: LoadedTask,
    adapter: Any,
    conn: sqlite3.Connection,
    exp_id: str,
    run_id: str,
    repetition: int,
    pair_key: str,
    order_index: int,
    artifact_dir: Path,
    use_docker: bool,
) -> None:
    task = loaded.definition
    started_at = utc_now()
    workspace_dir = artifact_dir / "workspace"
    cache_dir = artifact_dir.parent.parent / "_git-cache"

    # Materialize task repository from source/ if task-relative
    try:
        materialize_repo(loaded.task_dir, check=True)
    except MaterializeMismatchError as exc:
        storage_module.insert_run(
            conn,
            {
                "id": run_id,
                "experiment_id": exp_id,
                "task_id": task.id,
                "agent_name": adapter.agent_name,
                "repetition": repetition,
                "pair_key": pair_key,
                "order_index": order_index,
                "status": "setup_error",
                "requested_model": None,
                "reported_model": None,
                "cli_version": None,
                "starting_commit": "",
                "instruction_sha256": loaded.instruction_sha256,
                "environment_digest": "",
                "evaluator_digest": "",
                "started_at": started_at,
                "ended_at": utc_now(),
                "elapsed_seconds": 0.0,
                "exit_code": None,
                "error_category": "setup_error",
                "error_message": f"materialize mismatch: {exc}",
                "usage_json": "{}",
                "artifact_dir": str(artifact_dir),
            },
        )
        conn.commit()
        return
    except ConfigurationError as exc:
        storage_module.insert_run(
            conn,
            {
                "id": run_id,
                "experiment_id": exp_id,
                "task_id": task.id,
                "agent_name": adapter.agent_name,
                "repetition": repetition,
                "pair_key": pair_key,
                "order_index": order_index,
                "status": "setup_error",
                "requested_model": None,
                "reported_model": None,
                "cli_version": None,
                "starting_commit": "",
                "instruction_sha256": loaded.instruction_sha256,
                "environment_digest": "",
                "evaluator_digest": "",
                "started_at": started_at,
                "ended_at": utc_now(),
                "elapsed_seconds": 0.0,
                "exit_code": None,
                "error_category": "setup_error",
                "error_message": f"materialize failed: {exc}",
                "usage_json": "{}",
                "artifact_dir": str(artifact_dir),
            },
        )
        conn.commit()
        return

    repository = resolve_repository(loaded.task_dir, task.repository)

    # Placeholder run row so interruptions still persist.
    storage_module.insert_run(
        conn,
        {
            "id": run_id,
            "experiment_id": exp_id,
            "task_id": task.id,
            "agent_name": adapter.agent_name,
            "repetition": repetition,
            "pair_key": pair_key,
            "order_index": order_index,
            "status": "running",
            "requested_model": None,
            "reported_model": None,
            "cli_version": None,
            "starting_commit": "",
            "instruction_sha256": loaded.instruction_sha256,
            "environment_digest": environment_digest(loaded.task_dir, task.dockerfile),
            "evaluator_digest": "",
            "started_at": started_at,
            "ended_at": "",
            "elapsed_seconds": 0.0,
            "exit_code": None,
            "error_category": None,
            "error_message": None,
            "usage_json": "{}",
            "artifact_dir": str(artifact_dir),
        },
    )
    conn.commit()

    setup_error: str | None = None
    starting_commit = ""
    try:
        info = checkout_fresh(
            repository=repository, commit=task.commit, dest=workspace_dir, cache_dir=cache_dir
        )
        starting_commit = info.starting_commit
    except Exception as exc:
        setup_error = str(exc)[:2000]

    (artifact_dir / "prompt.txt").write_text(loaded.wrapped_prompt, encoding="utf-8")
    (artifact_dir / "metadata.json").write_text(
        json.dumps(
            {
                "experiment_id": exp_id,
                "run_id": run_id,
                "task_id": task.id,
                "agent": adapter.agent_name,
                "repetition": repetition,
                "pair_key": pair_key,
                "order_index": order_index,
                "instruction_sha256": loaded.instruction_sha256,
                "prompt_wrapper_version": loaded.prompt_wrapper_version,
                "starting_commit": starting_commit,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    if setup_error is not None:
        storage_module.update_run(
            conn,
            run_id,
            {
                "status": "setup_error",
                "ended_at": utc_now(),
                "error_category": "setup_error",
                "error_message": setup_error,
                "starting_commit": starting_commit,
            },
        )
        conn.commit()
        return

    # Agent phase.
    stdout_path = artifact_dir / "stdout.log"
    stderr_path = artifact_dir / "stderr.log"
    events_path = artifact_dir / "events.jsonl"
    timeout = min(task.timeout_seconds, config.execution.global_max_timeout_seconds)
    agent_result: Any = None
    try:
        if use_docker and hasattr(adapter, "build_argv"):
            agent_result = _run_agent_in_docker(
                config=config,
                task=task,
                adapter=adapter,
                prompt=loaded.wrapped_prompt,
                workspace_dir=workspace_dir,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                events_path=events_path,
                timeout_seconds=float(timeout),
                artifact_dir=artifact_dir,
            )
        else:
            agent_result = adapter.run(
                prompt=loaded.wrapped_prompt,
                workdir=workspace_dir,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                events_path=events_path,
                timeout_seconds=float(timeout),
            )
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        storage_module.update_run(
            conn,
            run_id,
            {
                "status": "agent_error",
                "ended_at": utc_now(),
                "elapsed_seconds": 0.0,
                "starting_commit": starting_commit,
                "error_category": "agent_error",
                "error_message": str(exc)[:2000],
            },
        )
        conn.commit()
        return

    # Diff + status artifacts (agent workspace only; never evaluator files).
    try:
        diff_text = workspace_diff(workspace_dir)
    except Exception:
        diff_text = ""
    _write_text(artifact_dir / "diff.patch", diff_text)
    try:
        git_status = subprocess.run(
            [  # noqa: S607 - intentional PATH lookup of explicit tool
                "git",
                "status",
                "--short",
            ],
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        git_status = ""
    _write_text(artifact_dir / "git-status.txt", git_status)
    _write_text(
        artifact_dir / "agent-result.json",
        json.dumps(
            {
                "agent": agent_result.agent_name,
                "status": str(agent_result.status),
                "exit_code": agent_result.exit_code,
                "elapsed_seconds": agent_result.elapsed_seconds,
                "requested_model": agent_result.requested_model,
                "reported_model": agent_result.reported_model,
                "cli_version": agent_result.cli_version,
                "error_category": str(agent_result.error_category)
                if agent_result.error_category
                else None,
                "error_message": agent_result.error_message,
                "usage": agent_result.usage.model_dump()
                if hasattr(agent_result.usage, "model_dump")
                else {},
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        redact=False,
    )

    storage_module.update_run(
        conn,
        run_id,
        {
            "status": str(agent_result.status),
            "requested_model": agent_result.requested_model,
            "reported_model": agent_result.reported_model,
            "cli_version": agent_result.cli_version,
            "starting_commit": starting_commit or task.commit,
            "ended_at": agent_result.ended_at,
            "elapsed_seconds": float(agent_result.elapsed_seconds),
            "exit_code": agent_result.exit_code,
            "error_category": str(agent_result.error_category)
            if agent_result.error_category
            else None,
            "error_message": agent_result.error_message,
            "usage_json": json.dumps(
                agent_result.usage.model_dump()
                if hasattr(agent_result.usage, "model_dump")
                else {},
                sort_keys=True,
            ),
        },
    )
    conn.commit()

    # Evaluation phase: fresh snapshot copy, no provider creds, trusted command.
    evaluator_dir = (loaded.task_dir / "evaluator").resolve()
    evaluator_out = artifact_dir / "evaluator"
    evaluator_out.mkdir(parents=True, exist_ok=True)
    eval_command = _resolve_eval_command(task.evaluator_command, evaluator_dir)
    # Build GateSpec from task scoring.
    gates = GateSpec.from_scoring(
        task.scoring,
        resolve=lambda c: _resolve_eval_command(c, evaluator_dir),
    )
    try:
        eval_result = run_evaluation(
            snapshot_dir=workspace_dir,
            evaluator_dir=evaluator_dir,
            evaluator_command=eval_command,
            output_dir=evaluator_out,
            timeout_seconds=float(task.max_test_seconds),
            use_docker=use_docker,
            gates=gates,
        )
    except Exception as exc:
        storage_module.update_run(
            conn, run_id, {"status": "evaluation_error", "error_category": "evaluation_error"}
        )
        storage_module.insert_evaluation(
            conn,
            {
                "id": new_id("eval"),
                "run_id": run_id,
                "status": "evaluation_error",
                "acceptance_pass": None,
                "exit_code": None,
                "duration_seconds": 0.0,
                "tests_passed": None,
                "tests_failed": None,
                "tests_skipped": None,
                "build_pass": None,
                "lint_pass": None,
                "typecheck_pass": None,
                "regression_pass": None,
                "output_json": json.dumps({"error": str(exc)[:2000]}),
                "evaluator_version": "",
            },
        )
        conn.commit()
        return

    storage_module.insert_evaluation(
        conn,
        {
            "id": new_id("eval"),
            "run_id": run_id,
            "status": str(eval_result.status),
            "acceptance_pass": 1
            if eval_result.acceptance_pass is True
            else (0 if eval_result.acceptance_pass is False else None),
            "exit_code": eval_result.exit_code,
            "duration_seconds": float(eval_result.duration_seconds),
            "tests_passed": eval_result.tests_passed,
            "tests_failed": eval_result.tests_failed,
            "tests_skipped": eval_result.tests_skipped,
            "build_pass": 1
            if eval_result.build_pass is True
            else (0 if eval_result.build_pass is False else None),
            "lint_pass": 1
            if eval_result.lint_pass is True
            else (0 if eval_result.lint_pass is False else None),
            "typecheck_pass": 1
            if eval_result.typecheck_pass is True
            else (0 if eval_result.typecheck_pass is False else None),
            "regression_pass": None,
            "output_json": json.dumps(
                {
                    "stdout_tail": eval_result.stdout[-4000:],
                    "stderr_tail": eval_result.stderr[-2000:],
                    "gates": eval_result.gate_outputs,
                }
            ),
            "evaluator_version": eval_result.evaluator_version,
        },
    )
    # Evaluator digest + env digest update.
    try:
        digest = evaluator_digest(evaluator_dir)
    except Exception:
        digest = ""
    storage_module.update_run(conn, run_id, {"evaluator_digest": digest})
    conn.commit()

    # Artifact index.
    for kind, rel in (
        ("prompt", "prompt.txt"),
        ("stdout", "stdout.log"),
        ("stderr", "stderr.log"),
        ("events", "events.jsonl"),
        ("agent-result", "agent-result.json"),
        ("diff", "diff.patch"),
        ("git-status", "git-status.txt"),
        ("metadata", "metadata.json"),
        ("eval-stdout", "evaluator/stdout.log"),
        ("eval-stderr", "evaluator/stderr.log"),
    ):
        path = artifact_dir / rel
        if not path.is_file():
            continue
        sha, size = _file_sha(path)
        storage_module.insert_artifact(
            conn,
            {
                "id": new_id("art"),
                "run_id": run_id,
                "kind": kind,
                "relative_path": rel,
                "sha256": sha,
                "size_bytes": size,
                "redacted": 0,
                "created_at": utc_now(),
            },
        )
    conn.commit()

    # Retention: remove workspace copy only when configured.
    if config.execution.workspace_cleanup == "remove":
        shutil.rmtree(workspace_dir, ignore_errors=True)


def _resolve_eval_command(command: list[str], evaluator_dir: Path) -> list[str]:
    """Map container-style `/evaluator/...` paths to the host evaluator dir (local mode)."""
    resolved: list[str] = []
    evaluator_dir = evaluator_dir.resolve()
    for part in command:
        if part == "/evaluator/run_tests.sh":
            candidate = evaluator_dir / "run_tests.sh"
            resolved.append(str(candidate) if candidate.is_file() else part)
        elif part.startswith("/evaluator/"):
            candidate = evaluator_dir / part[len("/evaluator/") :]
            resolved.append(str(candidate) if candidate.exists() else part)
        else:
            resolved.append(part)
    return resolved


def _run_agent_in_docker(
    *,
    config: BenchmarkConfig,
    task: Any,
    adapter: Any,
    prompt: str,
    workspace_dir: Path,
    stdout_path: Path,
    stderr_path: Path,
    events_path: Path,
    timeout_seconds: float,
    artifact_dir: Path,
) -> Any:
    """Execute a real CLI adapter inside a hardened container (§9)."""
    from ai_benchmark.docker_runner import ExecutionSpec, Mount, build_image, run_container
    from ai_benchmark.redaction import redact_text as _redact

    # task.dockerfile is task-relative; scheduler callers pass LoadedTask task dir?
    # Here `task` is the definition; resolve via workspace parent is unreliable,
    # so build the image from the task dir recorded in the artifact metadata is
    # skipped: use the prebuilt image tag and record the Dockerfile hash instead.
    image = f"codebench-task:{task.id}"
    environment_digest = ""
    with contextlib.suppress(Exception):
        # Best effort: image must already be built via `tasks validate --build`.
        pass
    _ = build_image  # referenced for the Docker path; validated in doctor
    argv: list[str] = adapter.build_argv(prompt)
    cpu = task.cpu_limit or config.execution.cpu_limit
    spec = ExecutionSpec(
        command=argv,
        workdir=workspace_dir,
        timeout_seconds=timeout_seconds,
        mounts=(Mount(source=workspace_dir, target="/workspace", read_only=False),),
        env={},
        cpu_limit=float(cpu),
        memory_limit=task.memory_limit or config.execution.memory_limit,
        pids_limit=task.pids_limit or config.execution.pids_limit,
        container_user=config.execution.container_user,
        network_enabled=bool(task.network_enabled_for_agent),
        image=image,
    )
    from datetime import datetime as _dt

    started_at = _dt.now(UTC).isoformat()
    import time as _time

    begin = _time.monotonic()
    result = run_container(spec, name=f"cb-agent-{artifact_dir.name[:16]}")
    elapsed = _time.monotonic() - begin
    stdout_path.write_text(result.stdout or "", encoding="utf-8")
    stderr_path.write_text(result.stderr or "", encoding="utf-8")
    if events_path is not None:
        events_path.write_text(result.stdout or "", encoding="utf-8")
    # Delegate parsing to the adapter when available.
    parse = getattr(adapter, "parse_container_output", None)
    if callable(parse):
        return parse(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            elapsed_seconds=elapsed,
            started_at=started_at,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            events_path=events_path,
            timed_out=result.timed_out,
            exit_code=result.exit_code,
            environment_digest=environment_digest,
        )
    # Fallback: minimal RunResult construction.
    from ai_agents.adapter import RunResult as _RunResult
    from ai_agents.adapter import categorize_exit as _cat
    from ai_schemas.codebench import UsageRecord as _Usage

    status, category = _cat(
        exit_code=result.exit_code, timed_out=result.timed_out, interrupted=False
    )
    response, _ = _redact((result.stdout or "")[:8000])
    return _RunResult(
        agent_name=adapter.agent_name,
        requested_model=None,
        reported_model=None,
        cli_version=getattr(adapter, "version", lambda: None)(),
        status=status,
        exit_code=result.exit_code,
        started_at=started_at,
        ended_at=_dt.now(UTC).isoformat(),
        elapsed_seconds=elapsed,
        response_text=response,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        events_path=str(events_path) if events_path else None,
        usage=_Usage(),
        error_category=category,
        error_message=None if status.value == "completed" else (result.stderr or "")[:2000],
    )


__all__ = [
    "ExperimentRequest",
    "ExperimentSummary",
    "docker_version",
    "host_info",
    "run_experiment",
    "utc_now",
]
