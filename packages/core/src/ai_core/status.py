"""Run/evaluation status primitives (stdlib only)."""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    """Agent-process outcome, separate from evaluator outcome (§8).

    A process that exits zero but fails hidden tests is ``COMPLETED``
    with an evaluation failure, not an adapter failure.
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
    """Trusted evaluator outcome (§11.1)."""

    PASS = "pass"  # noqa: S105 - status literal, not a password
    FAIL = "fail"
    EVALUATION_ERROR = "evaluation_error"
    NOT_EVALUATED = "not_evaluated"


class ErrorCategory(StrEnum):
    """Failure buckets for reporting (§12.1, §15)."""

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
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_PARTIAL = "completed_partial"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
