"""Demo end-to-end with fake agents (no docker, no providers)."""

from pathlib import Path

from ai_benchmark.evaluator import run_evaluation
from ai_benchmark.fake_agent import FakeAgentAdapter
from ai_benchmark.task_materialize import materialize_repo
from ai_benchmark.task_registry import load_task, resolve_repository, validate_task
from ai_benchmark.task_verify import apply_solution
from ai_benchmark.workspace import checkout_fresh
from ai_core.status import EvalStatus, RunStatus

DEMO_DIR = Path(__file__).resolve().parents[3] / "tasks" / "pilot" / "example-task"


def test_demo_validates():
    materialize_repo(DEMO_DIR, force=True)
    result = validate_task(DEMO_DIR, check_repo=True)
    assert result.ok, result.errors


def test_demo_original_fails_and_solution_passes(tmp_path: Path):
    materialize_repo(DEMO_DIR, force=True)
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

    # Apply reference solution; evaluator must pass.
    workspace = tmp_path / "solution"
    checkout_fresh(
        repository=repo,
        commit=loaded.definition.commit,
        dest=workspace,
        cache_dir=tmp_path / "cache",
    )
    apply_solution(DEMO_DIR, workspace)
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
    artifact = tmp_path / "artifacts"
    artifact.mkdir()
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
    materialize_repo(DEMO_DIR, force=True)
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