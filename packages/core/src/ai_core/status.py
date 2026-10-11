"""Run/evaluation status primitives (stdlib only)."""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    """Agent-process outcome, separate from evaluator outcome (§8).

    A process that exits zero but fails hidden tests is ``COMPLETED``
    with an evaluation failure, not an adapter failure.

    Values:
        PENDING: Task has been created but not yet started.
        RUNNING: Agent process is currently executing.
        COMPLETED: Agent process exited with code 0 (success).
        AGENT_ERROR: Agent process exited with non-zero code or crashed.
        TIMEOUT: Agent process exceeded its time limit.
        INTERRUPTED: Execution was interrupted (e.g., SIGINT).
        SETUP_ERROR: Failed to set up the execution environment.
        EVALUATION_ERROR: The trusted evaluator failed to run.
        CANCELLED: Execution was cancelled before completion.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    AGENT_ERROR = "agent_error"
    TIMEOUT = "timeout"
    INTERRUPTED = "interrupted"
    SETUP_ERROR = "setup_error"
    EVALUATION_ERROR = "evaluation_error"
    CANCELLED = "cancelled"


class EvalStatus(StrEnum):
    """Trusted evaluator outcome (§11.1).

    Values:
        PASS: All hidden tests passed.
        FAIL: At least one hidden test failed.
        EVALUATION_ERROR: The evaluator itself failed to run.
        NOT_EVALUATED: No evaluation was performed.
    """

    PASS = "pass"  # noqa: S105 - status literal, not a password
    FAIL = "fail"
    EVALUATION_ERROR = "evaluation_error"
    NOT_EVALUATED = "not_evaluated"


class ErrorCategory(StrEnum):
    """Failure buckets for reporting (§12.1, §15).

    Values:
        NONE: No error (success).
        TIMEOUT: Operation timed out.
        AGENT_ERROR: Agent process failed.
        SETUP_ERROR: Environment setup failed.
        EVALUATION_ERROR: Evaluator failed to run.
        INTERRUPTED: Execution was interrupted.
        CANCELLED: Execution was cancelled.
        VALIDATION: Input validation failed.
        UNKNOWN: Unclassified error.
    """

    NONE = "none"
    TIMEOUT = "timeout"
    AGENT_ERROR = "agent_error"
    SETUP_ERROR = "setup_error"
    EVALUATION_ERROR = "evaluation_error"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class ExperimentStatus(StrEnum):
    """Experiment execution status (§16).

    Benchmark execution success is distinct from coding-task success:
    an experiment can be ``COMPLETED`` even when agents fail tasks.

    Values:
        PENDING: Experiment created but not yet started.
        RUNNING: Experiment is currently executing.
        COMPLETED: All planned runs finished.
        COMPLETED_PARTIAL: Some runs finished, others missing.
        FAILED: Experiment failed before any runs.
        INTERRUPTED: Experiment was interrupted.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_PARTIAL = "completed_partial"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
