"""Demo end-to-end with fake agents (no docker, no providers)."""

from pathlib import Path

from ai_benchmark.evaluator import run_evaluation
from ai_benchmark.fake_agent import FakeAgentAdapter
from ai_benchmark.task_registry import load_task, resolve_repository, validate_task
from ai_benchmark.workspace import checkout_fresh
from ai_core.status import EvalStatus, RunStatus

DEMO_DIR = Path(__file__).resolve().parents[3] / "tasks" / "pilot" / "example-task"


def _ensure_demo_repo() -> None:
    """Regenerate the deterministic demo repo when missing (CI-safe)."""
    import os
    import shutil
    import subprocess

    repo = DEMO_DIR / "repo"
    source = DEMO_DIR / "source"
    if repo.is_dir() and (repo / ".git").is_dir():
        return
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    for name in ("calc.py", "README.md", "test_visible.py"):
        shutil.copy(source / name, repo / name)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "CodeBench Demo",
        "GIT_AUTHOR_EMAIL": "demo@example.invalid",
        "GIT_COMMITTER_NAME": "CodeBench Demo",
        "GIT_COMMITTER_EMAIL": "demo@example.invalid",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    }
    subprocess.run(
        ["git", "init"],  # noqa: S607 - intentional PATH lookup of explicit tool
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )
    subprocess.run(
        ["git", "add", "."],  # noqa: S607 - intentional PATH lookup of explicit tool
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )
    subprocess.run(
        [  # noqa: S607 - intentional PATH lookup of explicit tool
            "git",
            "commit",
            "-m",
            "demo: buggy add",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )


def test_demo_validates():
    _ensure_demo_repo()
    result = validate_task(DEMO_DIR, check_repo=True)
    assert result.ok, result.errors


def test_demo_original_fails_and_solution_passes(tmp_path: Path):
    _ensure_demo_repo()
    loaded = load_task(DEMO_DIR)
    repo = resolve_repository(DEMO_DIR, loaded.definition.repository)
    evaluator_dir = DEMO_DIR / "evaluator"

    # Original (buggy) checkout must fail hidden tests.
    original = tmp_path / "original"
    info = checkout_fresh(
        repository=repo,
        commit=loaded.definition.commit,
        dest=original,
        cache_dir=tmp_path / "cache",
    )
    assert info.starting_commit.lower() == loaded.definition.commit.lower()
    failing = run_evaluation(
        snapshot_dir=original,
        evaluator_dir=evaluator_dir,
        evaluator_command=["bash", str(evaluator_dir / "run_tests.sh")],
        output_dir=tmp_path / "eval-original",
        timeout_seconds=60,
        use_docker=False,
    )
    assert failing.status == EvalStatus.FAIL

    # Fake passing agent writes the fix; evaluator must pass.
    workspace = tmp_path / "agent-pass"
    checkout_fresh(
        repository=repo,
        commit=loaded.definition.commit,
        dest=workspace,
        cache_dir=tmp_path / "cache",
    )
    agent = FakeAgentAdapter(agent_name="fake", mode="pass")
    artifact = tmp_path / "artifacts"
    artifact.mkdir()
    run_result = agent.run(
        prompt=loaded.wrapped_prompt,
        workdir=workspace,
        stdout_path=artifact / "stdout.log",
        stderr_path=artifact / "stderr.log",
        events_path=artifact / "events.jsonl",
        timeout_seconds=60,
    )
    from ai_agents.adapter import RunResult

    assert isinstance(run_result, RunResult)
    assert run_result.status == RunStatus.COMPLETED
    passing = run_evaluation(
        snapshot_dir=workspace,
        evaluator_dir=evaluator_dir,
        evaluator_command=["bash", str(evaluator_dir / "run_tests.sh")],
        output_dir=tmp_path / "eval-pass",
        timeout_seconds=60,
        use_docker=False,
    )
    assert passing.status == EvalStatus.PASS

    # Fake failing agent stays failing.
    workspace2 = tmp_path / "agent-fail"
    checkout_fresh(
        repository=repo,
        commit=loaded.definition.commit,
        dest=workspace2,
        cache_dir=tmp_path / "cache",
    )
    bad = FakeAgentAdapter(agent_name="fake", mode="fail")
    bad.run(
        prompt=loaded.wrapped_prompt,
        workdir=workspace2,
        stdout_path=artifact / "stdout2.log",
        stderr_path=artifact / "stderr2.log",
        events_path=None,
        timeout_seconds=60,
    )
    still_failing = run_evaluation(
        snapshot_dir=workspace2,
        evaluator_dir=evaluator_dir,
        evaluator_command=["bash", str(evaluator_dir / "run_tests.sh")],
        output_dir=tmp_path / "eval-fail",
        timeout_seconds=60,
        use_docker=False,
    )
    assert still_failing.status == EvalStatus.FAIL


def test_agent_cannot_see_hidden_tests(tmp_path: Path):
    _ensure_demo_repo()
    loaded = load_task(DEMO_DIR)
    repo = resolve_repository(DEMO_DIR, loaded.definition.repository)
    workspace = tmp_path / "ws-hidden"
    checkout_fresh(
        repository=repo,
        commit=loaded.definition.commit,
        dest=workspace,
        cache_dir=tmp_path / "cache",
    )
    # Hidden test content must not exist in the agent workspace.
    hidden_text = (DEMO_DIR / "evaluator" / "tests" / "test_hidden.py").read_text()
    for path in workspace.rglob("*.py"):
        assert "test_add_positive" not in path.read_text(encoding="utf-8")
    assert "test_add_positive" in hidden_text
    # Instruction must not leak hidden assertions.
    assert "test_add_positive" not in loaded.instruction_text
