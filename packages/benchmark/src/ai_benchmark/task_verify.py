"""Solution overlay application and task verification (§11.4)."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ai_benchmark.evaluator import GateSpec, run_evaluation
from ai_benchmark.task_materialize import materialize_repo
from ai_benchmark.task_registry import load_task, resolve_repository, resolve_evaluator_command
from ai_benchmark.workspace import checkout_fresh
from ai_core.errors import ConfigurationError
from ai_core.status import EvalStatus


def apply_solution(task_dir: Path, workspace: Path) -> list[Path]:
    """Copy solution overlay files to workspace.

    Args:
        task_dir: Path to task directory containing solution/files/
        workspace: Destination workspace directory

    Returns:
        List of copied file paths (relative to workspace)

    Raises:
        ConfigurationError: When overlay dir is missing or empty, or path traversal detected
    """
    solution_dir = task_dir / "solution" / "files"
    if not solution_dir.is_dir():
        raise ConfigurationError(f"solution/files/ missing: {solution_dir}")
    copied: list[Path] = []
    for src in solution_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(solution_dir)
        # Safe join - prevent path traversal
        if any(part == ".." for part in rel.parts):
            raise ConfigurationError(f"path traversal in solution overlay: {rel}")
        dst = workspace / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    if not copied:
        raise ConfigurationError(f"solution/files/ empty: {solution_dir}")
    return copied


@dataclass(frozen=True, slots=True)
class TaskVerification:
    task_id: str
    original_status: EvalStatus | None
    solution_status: EvalStatus | None
    ok: bool
    errors: tuple[str, ...]


def verify_task(task_dir: Path, *, work_dir: Path, use_docker: bool = False) -> TaskVerification:
    """Verify a task's oracle: original fails, solution passes.

    Steps:
    1. Load task and materialize repo
    2. Checkout original commit, run evaluator → expect FAIL
    3. Checkout original commit again, apply solution, run evaluator → expect PASS

    Args:
        task_dir: Path to task directory
        work_dir: Working directory for temporary checkouts
        use_docker: Whether to use Docker for evaluation

    Returns:
        TaskVerification with results
    """
    errors: list[str] = []

    # Load task and materialize
    try:
        loaded = load_task(task_dir)
        materialize_repo(task_dir, check=False, force=True)
    except (ConfigurationError, Exception) as exc:
        return TaskVerification(
            task_id=task_dir.name,
            original_status=None,
            solution_status=None,
            ok=False,
            errors=(f"load/materialize failed: {exc}",),
        )

    task = loaded.definition
    evaluator_dir = (task_dir / "evaluator").resolve()
    repository = resolve_repository(task_dir, task.repository)
    eval_command = resolve_evaluator_command(task.evaluator_command, evaluator_dir)

    # GateSpec from task scoring
    gates = GateSpec.from_scoring(
        task.scoring,
        resolve=lambda c: resolve_evaluator_command(c, evaluator_dir),
    )

    # Original commit
    original_dir = work_dir / "original"
    try:
        checkout_fresh(
            repository=repository,
            commit=task.commit,
            dest=original_dir,
            cache_dir=work_dir / "cache",
        )
    except Exception as exc:
        return TaskVerification(
            task_id=task.id,
            original_status=None,
            solution_status=None,
            ok=False,
            errors=(f"checkout original failed: {exc}",),
        )

    # Evaluate original
    original_eval_dir = work_dir / "eval-original"
    original_eval_dir.mkdir(parents=True, exist_ok=True)
    try:
        orig_result = run_evaluation(
            snapshot_dir=original_dir,
            evaluator_dir=evaluator_dir,
            evaluator_command=eval_command,
            output_dir=original_eval_dir,
            timeout_seconds=float(task.max_test_seconds),
            use_docker=use_docker,
            gates=gates,
        )
    except Exception as exc:
        return TaskVerification(
            task_id=task.id,
            original_status=None,
            solution_status=None,
            ok=False,
            errors=(f"original evaluation error: {exc}",),
        )

    if orig_result.status == EvalStatus.PASS:
        errors.append("original commit passes the evaluator: hidden tests are not a working oracle")
    elif orig_result.status == EvalStatus.EVALUATION_ERROR:
        errors.append(f"original evaluation error: {orig_result.stderr[-2000:]}")

    # Solution commit
    solution_dir = work_dir / "solution"
    try:
        checkout_fresh(
            repository=repository,
            commit=task.commit,
            dest=solution_dir,
            cache_dir=work_dir / "cache",
        )
    except Exception as exc:
        return TaskVerification(
            task_id=task.id,
            original_status=orig_result.status,
            solution_status=None,
            ok=False,
            errors=(f"checkout solution failed: {exc}",) + tuple(errors),
        )

    # Apply solution overlay
    try:
        apply_solution(task_dir, solution_dir)
    except ConfigurationError as exc:
        return TaskVerification(
            task_id=task.id,
            original_status=orig_result.status,
            solution_status=None,
            ok=False,
            errors=(f"apply solution failed: {exc}",) + tuple(errors),
        )

    # Evaluate solution
    solution_eval_dir = work_dir / "eval-solution"
    solution_eval_dir.mkdir(parents=True, exist_ok=True)
    try:
        sol_result = run_evaluation(
            snapshot_dir=solution_dir,
            evaluator_dir=evaluator_dir,
            evaluator_command=eval_command,
            output_dir=solution_eval_dir,
            timeout_seconds=float(task.max_test_seconds),
            use_docker=use_docker,
            gates=gates,
        )
    except Exception as exc:
        return TaskVerification(
            task_id=task.id,
            original_status=orig_result.status,
            solution_status=None,
            ok=False,
            errors=(f"solution evaluation error: {exc}",) + tuple(errors),
        )

    if sol_result.status != EvalStatus.PASS:
        # Check which required gates failed
        failed_gates: list[str] = []
        if gates.build_required and sol_result.build_pass is False:
            failed_gates.append("build")
        if gates.lint_required and sol_result.lint_pass is False:
            failed_gates.append("lint")
        if gates.typecheck_required and sol_result.typecheck_pass is False:
            failed_gates.append("typecheck")
        if failed_gates:
            errors.append(f"solution fails required gates: {', '.join(failed_gates)}")
        else:
            errors.append(f"solution evaluation status: {sol_result.status.value}")

    ok = not errors
    return TaskVerification(
        task_id=task.id,
        original_status=orig_result.status,
        solution_status=sol_result.status,
        ok=ok,
        errors=tuple(errors),
    )