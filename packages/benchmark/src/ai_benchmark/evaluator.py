"""Trusted evaluator (§9.4, §11). Agent output never trusted; command is fixed."""

from __future__ import annotations

import hashlib
import re
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

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
    """Specification for quality gates (build, lint, typecheck).

    Attributes:
        build: Command tuple for the build gate.
        lint: Command tuple for the lint gate.
        typecheck: Command tuple for the typecheck gate.
        build_required: Whether the build gate is required to pass.
        lint_required: Whether the lint gate is required to pass.
        typecheck_required: Whether the typecheck gate is required to pass.
    """

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
        """Create a GateSpec from a TaskScoring configuration.

        Args:
            scoring: The task scoring configuration.
            resolve: Optional function to resolve command paths (e.g., mapping
                container paths to host paths).

        Returns:
            A new GateSpec instance.
        """
        resolve = resolve or (lambda c: c)
        return cls(
            build=tuple(resolve(scoring.build_command)) if scoring.build_command else (),
            lint=tuple(resolve(scoring.lint_command)) if scoring.lint_command else (),
            typecheck=tuple(resolve(scoring.typecheck_command))
            if scoring.typecheck_command
            else (),
            build_required=scoring.build_required,
            lint_required=scoring.lint_required,
            typecheck_required=scoring.typecheck_required,
        )

    def configured(self) -> dict[str, tuple[str, ...]]:
        """Return only the gates that have commands configured.

        Returns:
            Dictionary mapping gate names to their command tuples.
        """
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
    """Result of running the trusted evaluator.

    Attributes:
        status: Overall evaluation status.
        acceptance_pass: Whether the acceptance tests passed (None if not evaluated).
        exit_code: Process exit code (None if timed out).
        duration_seconds: Total execution time in seconds.
        stdout: Captured standard output.
        stderr: Captured standard error.
        tests_passed: Number of tests passed (None if not parsed).
        tests_failed: Number of tests failed (None if not parsed).
        tests_skipped: Number of tests skipped (None if not parsed).
        evaluator_version: SHA256 digest of evaluator files.
        build_pass: Whether the build gate passed (None if not run).
        lint_pass: Whether the lint gate passed (None if not run).
        typecheck_pass: Whether the typecheck gate passed (None if not run).
        gate_outputs: Captured output from each gate (last 2000 chars).
    """

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
    """Best-effort parse of ``passed=.. failed=.. skipped=..`` or pytest summaries.

    Args:
        stdout: The standard output from the test runner.

    Returns:
        A tuple of (passed, failed, skipped) counts, or ``None`` if not found.
    """

    def _find(name: str) -> int | None:
        match = re.search(rf"{name}\s*[:=]\s*(\d+)", stdout)
        if match:
            return int(match.group(1))
        # pytest style: "3 passed", "1 failed", "2 skipped"
        match = re.search(rf"(\d+)\s+{name}\b", stdout)
        return int(match.group(1)) if match else None

    return _find("passed"), _find("failed"), _find("skipped")


def evaluator_digest(evaluator_dir: Path) -> str:
    """Hash evaluator scripts/tests for integrity metadata (§11.2).

    Computes a SHA256 hash of all files in the evaluator directory,
    excluding ``__pycache__``, ``.pytest_cache``, and ``.pyc`` files.

    Args:
        evaluator_dir: Path to the evaluator directory.

    Returns:
        Hexadecimal SHA256 digest string.
    """
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
    """Execute a gate command in the eval workspace.

    Args:
        command: The command to execute as a list of arguments.
        eval_workspace: The evaluation workspace directory.
        evaluator_dir: The evaluator directory (mounted read-only).
        output_dir: The output directory for logs.
        timeout_seconds: Maximum execution time in seconds.
        image: Docker image to use (if using Docker).
        use_docker: Whether to run in Docker or locally.
        name: Container/process name for identification.

    Returns:
        The result of the command execution.

    Raises:
        ConfigurationError: If Docker is requested but unavailable.
    """
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

    This function executes the evaluator command in an isolated environment
    to verify the agent's changes. It runs acceptance tests first, then
    optionally runs configured quality gates (build, lint, typecheck).

    Args:
        snapshot_dir: Directory containing the agent's modified workspace snapshot.
        evaluator_dir: Directory containing the trusted evaluator scripts/tests.
        evaluator_command: The command to run the evaluator (e.g. ``bash /evaluator/run_tests.sh``).
        output_dir: Directory where evaluation output logs will be written.
        timeout_seconds: Maximum execution time in seconds.
        image: Docker image to use if running in Docker (default: "python:3.12-slim").
        use_docker: Whether to run in Docker. If None, auto-detects Docker availability.
        gates: Optional GateSpec specifying quality gates to run.

    Returns:
        EvaluatorResult containing status, pass/fail, timing, and output details.

    Raises:
        ConfigurationError: If evaluator command is empty, snapshot/evaluator
            directories are missing, or Docker is requested but unavailable.
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
            # Gate timeout -> EVALUATION_ERROR, acceptance_pass=None, gate passes None
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
