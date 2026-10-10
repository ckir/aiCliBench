"""Stable, provider-independent domain primitives.

This package must stay dependency-light and must never import provider SDKs,
web frameworks, database drivers, or plugin implementations.
"""

from ai_core.errors import (
    AiCoreError,
    AuthorizationError,
    ConfigurationError,
    OperationTimeoutError,
    ProviderError,
    ToolExecutionError,
    ValidationError,
)
from ai_core.ids import is_valid_id, new_id
from ai_core.result import Result
from ai_core.status import ErrorCategory, EvalStatus, ExperimentStatus, RunStatus

__all__ = [
    "AiCoreError",
    "AuthorizationError",
    "ConfigurationError",
    "ErrorCategory",
    "EvalStatus",
    "ExperimentStatus",
    "OperationTimeoutError",
    "ProviderError",
    "Result",
    "RunStatus",
    "ToolExecutionError",
    "ValidationError",
    "is_valid_id",
    "new_id",
]
