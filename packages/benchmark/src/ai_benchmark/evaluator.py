"""Trusted evaluator (§9.4, §11). Agent output never trusted; command is fixed."""

from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from ai_benchmark.docker_runner import (
    ExecutionSpec,
    Mount,
    docker_available,
    run_container,
    run_local,
)
from ai_core.errors import ConfigurationError
from ai_core.status import EvalStatus


@dataclass(frozen=True, slots=True)
class EvaluatorResult:
    status: EvalStatus
    acceptance_pass: bool | None
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    tests_passed: int | None
    tests_failed: int | None
    tests_skipped: int | None
    evaluator_version: str


def _parse_counts(stdout: str) -> tuple[int | None, int | None, int | None]:
    """Best-effort parse of `passed=.. failed=.. skipped=..` or pytest summaries."""

    def _find(name: str) -> int | None:
        match = re.search(rf"{name}\s*[:=]\s*(\d+)", stdout)
        if match:
            return int(match.group(1))
        # pytest style: "3 passed", "1 failed", "2 skipped"
        match = re.search(rf"(\d+)\s+{name}\b", stdout)
        return int(match.group(1)) if match else None

    return _find("passed"), _find("failed"), _find("skipped")


def evaluator_digest(evaluator_dir: Path) -> str:
    """Hash evaluator scripts/tests for integrity metadata (§11.2)."""
    hasher = hashlib.sha256()
    for path in sorted(evaluator_dir.rglob("*")):
        if path.is_file():
            hasher.update(path.name.encode())
            hasher.update(path.read_bytes())
    return hasher.hexdigest()


def run_evaluation(
    *,
    snapshot_dir: Path,
    evaluator_dir: Path,
    evaluator_command: list[str],
    output_dir: Path,
    timeout_seconds: float,
    image: str = "python:3.12-slim",
    use_docker: bool | None = None,
) -> EvaluatorResult:
    """Run the trusted acceptance command on a snapshot copy.

    - Agent snapshot is copied (read-only intent) into a fresh eval workspace.
    - Evaluator files are mounted read-only and only here, never in agent phase.
    - No provider credentials are passed.
    """
    if not evaluator_command:
        raise ConfigurationError("empty evaluator command")
    if not snapshot_dir.is_dir():
        raise ConfigurationError(f"snapshot missing: {snapshot_dir}")
    if not evaluator_dir.is_dir():
        raise ConfigurationError(f"evaluator missing: {evaluator_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    eval_workspace = output_dir / "eval-workspace"
    if eval_workspace.exists():
        shutil.rmtree(eval_workspace)
    shutil.copytree(snapshot_dir, eval_workspace, symlinks=False)

    version = evaluator_digest(evaluator_dir)
    should_use_docker = docker_available() if use_docker is None else use_docker
    started = time.monotonic()
    if should_use_docker:
        if not docker_available():
            raise ConfigurationError("docker requested but unavailable")
        spec = ExecutionSpec(
            command=evaluator_command,
            workdir=Path("/workspace"),
            timeout_seconds=timeout_seconds,
            mounts=(
                Mount(source=eval_workspace, target="/workspace", read_only=False),
                Mount(source=evaluator_dir, target="/evaluator", read_only=True),
                Mount(source=output_dir, target="/output", read_only=False),
            ),
            network_enabled=False,
            image=image,
        )
        result = run_container(spec, name=f"cb-eval-{int(started)}")
    else:
        # Local fallback: evaluator dir is NOT copied into snapshot; command
        # runs with cwd=snapshot copy and EVALUATOR_DIR env pointing outside.
        spec = ExecutionSpec(
            command=evaluator_command,
            workdir=eval_workspace,
            timeout_seconds=timeout_seconds,
            env={
                "EVALUATOR_DIR": str(evaluator_dir),
                "OUTPUT_DIR": str(output_dir),
                "WORKSPACE": str(eval_workspace),
                "PYTHONPATH": str(eval_workspace),
            },
        )
        result = run_local(spec)
    duration = time.monotonic() - started
    (output_dir / "stdout.log").write_text(result.stdout, encoding="utf-8")
    (output_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")

    if result.timed_out:
        return EvaluatorResult(
            status=EvalStatus.EVALUATION_ERROR,
            acceptance_pass=None,
            exit_code=None,
            duration_seconds=duration,
            stdout=result.stdout,
            stderr=result.stderr,
            tests_passed=None,
            tests_failed=None,
            tests_skipped=None,
            evaluator_version=version,
        )
    if result.exit_code == 0:
        passed, failed, skipped = _parse_counts(result.stdout)
        return EvaluatorResult(
            status=EvalStatus.PASS,
            acceptance_pass=True,
            exit_code=0,
            duration_seconds=duration,
            stdout=result.stdout,
            stderr=result.stderr,
            tests_passed=passed,
            tests_failed=failed,
            tests_skipped=skipped,
            evaluator_version=version,
        )
    if result.exit_code is None:
        return EvaluatorResult(
            status=EvalStatus.EVALUATION_ERROR,
            acceptance_pass=None,
            exit_code=None,
            duration_seconds=duration,
            stdout=result.stdout,
            stderr=result.stderr,
            tests_passed=None,
            tests_failed=None,
            tests_skipped=None,
            evaluator_version=version,
        )
    passed, failed, skipped = _parse_counts(result.stdout)
    return EvaluatorResult(
        status=EvalStatus.FAIL,
        acceptance_pass=False,
        exit_code=result.exit_code,
        duration_seconds=duration,
        stdout=result.stdout,
        stderr=result.stderr,
        tests_passed=passed,
        tests_failed=failed,
        tests_skipped=skipped,
        evaluator_version=version,
    )
