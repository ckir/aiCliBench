"""Trusted evaluator (§9.4, §11). Agent output never trusted; command is fixed."""

from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ai_benchmark.docker_runner import (
    ContainerResult,
    ExecutionSpec,
    Mount,
    docker_available,
    run_container,
    run_local,
)
from ai_core.errors import ConfigurationError
from ai_core.status import EvalStatus
from ai_schemas.codebench import TaskScoring


@dataclass(frozen=True, slots=True)
class GateSpec:
    build: tuple[str, ...] = ()
    lint: tuple[str, ...] = ()
    typecheck: tuple[str, ...] = ()
    build_required: bool = False
    lint_required: bool = False
    typecheck_required: bool = False

    @classmethod
    def from_scoring(
        cls,
        scoring: TaskScoring,
        *,
        resolve: Callable[[list[str]], list[str]] | None = None,
    ) -> GateSpec:
        resolve = resolve or (lambda c: c)
        return cls(
            build=tuple(resolve(scoring.build_command)) if scoring.build_command else (),
            lint=tuple(resolve(scoring.lint_command)) if scoring.lint_command else (),
            typecheck=tuple(resolve(scoring.typecheck_command)) if scoring.typecheck_command else (),
            build_required=scoring.build_required,
            lint_required=scoring.lint_required,
            typecheck_required=scoring.typecheck_required,
        )

    def configured(self) -> dict[str, tuple[str, ...]]:
        out: dict[str, tuple[str, ...]] = {}
        if self.build:
            out["build"] = self.build
        if self.lint:
            out["lint"] = self.lint
        if self.typecheck:
            out["typecheck"] = self.typecheck
        return out


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
    build_pass: bool | None = None
    lint_pass: bool | None = None
    typecheck_pass: bool | None = None
    gate_outputs: dict[str, str] = field(default_factory=dict)


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
            if any(part in ("__pycache__", ".pytest_cache") for part in path.parts):
                continue
            if path.suffix == ".pyc":
                continue
            hasher.update(path.name.encode())
            hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _execute(
    command: list[str],
    *,
    eval_workspace: Path,
    evaluator_dir: Path,
    output_dir: Path,
    timeout_seconds: float,
    image: str,
    use_docker: bool,
    name: str,
) -> ContainerResult:
    """Execute a gate command in the eval workspace."""
    if use_docker:
        if not docker_available():
            raise ConfigurationError("docker requested but unavailable")
        spec = ExecutionSpec(
            command=command,
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
        return run_container(spec, name=name)
    else:
        spec = ExecutionSpec(
            command=command,
            workdir=eval_workspace,
            timeout_seconds=timeout_seconds,
            env={
                "EVALUATOR_DIR": str(evaluator_dir),
                "OUTPUT_DIR": str(output_dir),
                "WORKSPACE": str(eval_workspace),
                "PYTHONPATH": str(eval_workspace),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        return run_local(spec)


def run_evaluation(
    *,
    snapshot_dir: Path,
    evaluator_dir: Path,
    evaluator_command: list[str],
    output_dir: Path,
    timeout_seconds: float,
    image: str = "python:3.12-slim",
    use_docker: bool | None = None,
    gates: GateSpec | None = None,
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

    # Run acceptance tests first
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
        spec = ExecutionSpec(
            command=evaluator_command,
            workdir=eval_workspace,
            timeout_seconds=timeout_seconds,
            env={
                "EVALUATOR_DIR": str(evaluator_dir),
                "OUTPUT_DIR": str(output_dir),
                "WORKSPACE_DIR": str(eval_workspace),
                "WORKSPACE": str(eval_workspace),
                "PYTHONPATH": str(eval_workspace),
                "PYTHONDONTWRITEBYTECODE": "1",
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

    # Determine acceptance pass/fail
    if result.exit_code == 0:
        acceptance_pass = True
        passed, failed, skipped = _parse_counts(result.stdout)
    elif result.exit_code is None:
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
    else:
        acceptance_pass = False
        passed, failed, skipped = _parse_counts(result.stdout)

    # If no gates configured, return early
    if gates is None:
        return EvaluatorResult(
            status=EvalStatus.PASS if acceptance_pass else EvalStatus.FAIL,
            acceptance_pass=acceptance_pass,
            exit_code=result.exit_code,
            duration_seconds=duration,
            stdout=result.stdout,
            stderr=result.stderr,
            tests_passed=passed,
            tests_failed=failed,
            tests_skipped=skipped,
            evaluator_version=version,
        )

    # Run configured gates
    gate_results: dict[str, bool] = {}
    gate_outputs: dict[str, str] = {}

    for gate_name, gate_cmd in gates.configured().items():
        gate_started = time.monotonic()
        gate_result = _execute(
            list(gate_cmd),
            eval_workspace=eval_workspace,
            evaluator_dir=evaluator_dir,
            output_dir=output_dir,
            timeout_seconds=timeout_seconds,
            image=image,
            use_docker=should_use_docker,
            name=f"cb-gate-{gate_name}-{int(gate_started)}",
        )
        gate_duration = time.monotonic() - gate_started

        # Capture last 2000 chars of stdout+stderr
        combined = (gate_result.stdout or "") + (gate_result.stderr or "")
        gate_outputs[gate_name] = combined[-2000:]

        if gate_result.timed_out:
            # Timeout on any gate → EVALUATION_ERROR, acceptance_pass=None, gate passes recorded as None
            return EvaluatorResult(
                status=EvalStatus.EVALUATION_ERROR,
                acceptance_pass=None,
                exit_code=None,
                duration_seconds=duration + gate_duration,
                stdout=result.stdout,
                stderr=result.stderr,
                tests_passed=passed,
                tests_failed=failed,
                tests_skipped=skipped,
                evaluator_version=version,
                build_pass=None,
                lint_pass=None,
                typecheck_pass=None,
                gate_outputs=gate_outputs,
            )

        gate_pass = gate_result.exit_code == 0
        gate_results[gate_name] = gate_pass

    # Determine final status: acceptance_pass AND all required gates pass
    required_pass = True
    if gates.build_required:
        required_pass = required_pass and gate_results.get("build", False)
    if gates.lint_required:
        required_pass = required_pass and gate_results.get("lint", False)
    if gates.typecheck_required:
        required_pass = required_pass and gate_results.get("typecheck", False)

    final_pass = acceptance_pass and required_pass

    return EvaluatorResult(
        status=EvalStatus.PASS if final_pass else EvalStatus.FAIL,
        acceptance_pass=final_pass,
        exit_code=result.exit_code,
        duration_seconds=duration,
        stdout=result.stdout,
        stderr=result.stderr,
        tests_passed=passed,
        tests_failed=failed,
        tests_skipped=skipped,
        evaluator_version=version,
        build_pass=gate_results.get("build"),
        lint_pass=gate_results.get("lint"),
        typecheck_pass=gate_results.get("typecheck"),
        gate_outputs=gate_outputs,
    )