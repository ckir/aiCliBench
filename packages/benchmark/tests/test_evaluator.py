from pathlib import Path

from ai_benchmark.evaluator import evaluator_digest, run_evaluation, GateSpec
from ai_core.status import EvalStatus
from ai_schemas import TaskScoring


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


def _gate_script(root: Path, name: str, exit_code: int) -> list[str]:
    script = root / f"{name}.sh"
    script.write_text(
        f"#!/bin/bash\necho 'gate {name} running'\nexit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return ["bash", str(script)]


def test_gate_required_fail_makes_evaluation_fail(tmp_path: Path):
    snap = _make_snapshot(tmp_path / "s", "x\n")
    ev = _make_evaluator(tmp_path / "e", passes=True)
    gates = GateSpec(lint=tuple(_gate_script(tmp_path, "lint", 1)), lint_required=True)
    r = run_evaluation(
        snapshot_dir=snap,
        evaluator_dir=ev,
        evaluator_command=["bash", str(ev / "run_tests.sh")],
        output_dir=tmp_path / "o",
        timeout_seconds=30,
        use_docker=False,
        gates=gates,
    )
    assert r.status == EvalStatus.FAIL and r.acceptance_pass is False
    assert r.lint_pass is False and r.build_pass is None and "lint" in r.gate_outputs


def test_gate_optional_fail_recorded_only(tmp_path: Path):
    snap = _make_snapshot(tmp_path / "s2", "x\n")
    ev = _make_evaluator(tmp_path / "e2", passes=True)
    gates = GateSpec(lint=tuple(_gate_script(tmp_path, "lint2", 1)), lint_required=False)
    r = run_evaluation(
        snapshot_dir=snap,
        evaluator_dir=ev,
        evaluator_command=["bash", str(ev / "run_tests.sh")],
        output_dir=tmp_path / "o2",
        timeout_seconds=30,
        use_docker=False,
        gates=gates,
    )
    assert r.status == EvalStatus.PASS
    assert r.acceptance_pass is True
    assert r.lint_pass is False
    assert "lint" in r.gate_outputs


def test_gate_pass_does_not_rescue_failed_acceptance(tmp_path: Path):
    snap = _make_snapshot(tmp_path / "s3", "x\n")
    ev = _make_evaluator(tmp_path / "e3", passes=False)
    gates = GateSpec(build=tuple(_gate_script(tmp_path, "build", 0)), build_required=True)
    r = run_evaluation(
        snapshot_dir=snap,
        evaluator_dir=ev,
        evaluator_command=["bash", str(ev / "run_tests.sh")],
        output_dir=tmp_path / "o3",
        timeout_seconds=30,
        use_docker=False,
        gates=gates,
    )
    assert r.status == EvalStatus.FAIL
    assert r.acceptance_pass is False
    assert r.build_pass is True


def test_gate_timeout_is_evaluation_error(tmp_path: Path):
    snap = _make_snapshot(tmp_path / "s4", "x\n")
    ev = _make_evaluator(tmp_path / "e4", passes=True)
    gates = GateSpec(build=tuple(["python3", "-c", "import time; time.sleep(5)"]), build_required=True)
    r = run_evaluation(
        snapshot_dir=snap,
        evaluator_dir=ev,
        evaluator_command=["bash", str(ev / "run_tests.sh")],
        output_dir=tmp_path / "o4",
        timeout_seconds=0.3,
        use_docker=False,
        gates=gates,
    )
    assert r.status == EvalStatus.EVALUATION_ERROR
    assert r.acceptance_pass is None
    assert r.build_pass is None


def test_gate_spec_from_scoring_resolves_commands():
    spec = GateSpec.from_scoring(
        TaskScoring(build_required=True, build_command=["bash", "/evaluator/b.sh"]),
        resolve=lambda c: ["R", *c],
    )
    assert spec.build == ("R", "bash", "/evaluator/b.sh")
    assert spec.configured() == {"build": spec.build}


def test_evaluator_digest_ignores_pycache(tmp_path: Path):
    ev = _make_evaluator(tmp_path / "d2", passes=True)
    before = evaluator_digest(ev)
    (ev / "__pycache__").mkdir()
    (ev / "__pycache__" / "x.cpython-313.pyc").write_bytes(b"\x00")
    (ev / "run_tests.pyc").write_bytes(b"\x00")
    (ev / ".pytest_cache").mkdir()
    (ev / ".pytest_cache" / "v").write_text("1")
    assert evaluator_digest(ev) == before
