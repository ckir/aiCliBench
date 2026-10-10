from pathlib import Path

from ai_benchmark.evaluator import evaluator_digest, run_evaluation
from ai_core.status import EvalStatus


def _make_snapshot(root: Path, content: str) -> Path:
    snap = root / "snapshot"
    snap.mkdir(parents=True, exist_ok=True)
    (snap / "app.py").write_text(content, encoding="utf-8")
    return snap


def _make_evaluator(root: Path, *, passes: bool) -> Path:
    eval_dir = root / "evaluator"
    eval_dir.mkdir(parents=True, exist_ok=True)
    script = eval_dir / "run_tests.sh"
    if passes:
        script.write_text(
            "#!/bin/bash\necho 'passed: 1 failed: 0 skipped: 0'\nexit 0\n", encoding="utf-8"
        )
    else:
        script.write_text(
            "#!/bin/bash\necho 'passed: 0 failed: 1 skipped: 0'\nexit 1\n",
            encoding="utf-8",
        )
    script.chmod(0o755)
    return eval_dir


def test_evaluator_pass_and_fail(tmp_path: Path):
    snap = _make_snapshot(tmp_path / "a", "VALUE = 1\n")
    eval_ok = _make_evaluator(tmp_path / "b", passes=True)
    result = run_evaluation(
        snapshot_dir=snap,
        evaluator_dir=eval_ok,
        evaluator_command=["bash", str(eval_ok / "run_tests.sh")],
        output_dir=tmp_path / "out-ok",
        timeout_seconds=30,
        use_docker=False,
    )
    assert result.status == EvalStatus.PASS
    assert result.acceptance_pass is True
    assert result.exit_code == 0
    assert result.tests_passed == 1

    eval_bad = _make_evaluator(tmp_path / "c", passes=False)
    failed = run_evaluation(
        snapshot_dir=snap,
        evaluator_dir=eval_bad,
        evaluator_command=["bash", str(eval_bad / "run_tests.sh")],
        output_dir=tmp_path / "out-bad",
        timeout_seconds=30,
        use_docker=False,
    )
    assert failed.status == EvalStatus.FAIL
    assert failed.acceptance_pass is False
    assert failed.tests_failed == 1


def test_evaluator_timeout_is_infra_error(tmp_path: Path):
    snap = _make_snapshot(tmp_path / "a2", "x\n")
    eval_dir = tmp_path / "eval2"
    eval_dir.mkdir(parents=True, exist_ok=True)
    result = run_evaluation(
        snapshot_dir=snap,
        evaluator_dir=eval_dir,
        evaluator_command=["python3", "-c", "import time; time.sleep(5)"],
        output_dir=tmp_path / "out-timeout",
        timeout_seconds=0.3,
        use_docker=False,
    )
    assert result.status == EvalStatus.EVALUATION_ERROR
    assert result.acceptance_pass is None


def test_evaluator_digest_stable(tmp_path: Path):
    eval_dir = _make_evaluator(tmp_path / "d", passes=True)
    assert evaluator_digest(eval_dir) == evaluator_digest(eval_dir)
