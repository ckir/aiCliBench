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

__all__ = [
    "AiCoreError",
    "AuthorizationError",
    "ConfigurationError",
    "OperationTimeoutError",
    "ProviderError",
    "Result",
    "ToolExecutionError",
    "ValidationError",
    "is_valid_id",
    "new_id",
]
