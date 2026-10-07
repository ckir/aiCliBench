"""Stable, provider-independent error hierarchy."""

from __future__ import annotations


class AiCoreError(Exception):
    """Base class for all product errors."""


class ConfigurationError(AiCoreError):
    """Raised when explicit configuration is missing or invalid."""


class ValidationError(AiCoreError):
    """Raised when untrusted input (model output, tool args, payloads) fails validation."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class AuthorizationError(AiCoreError):
    """Raised when a side-effecting capability is not authorized."""

    def __init__(self, message: str, *, tool_name: str | None = None) -> None:
        super().__init__(message)
        self.tool_name = tool_name


class ToolExecutionError(AiCoreError):
    """Raised when a tool/capability fails downstream."""

    def __init__(self, message: str, *, tool_name: str | None = None) -> None:
        super().__init__(message)
        self.tool_name = tool_name


class ProviderError(AiCoreError):
    """Normalized provider/transport failure. Provider SDK errors never escape adapters."""

    def __init__(self, message: str, *, provider: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class OperationTimeoutError(AiCoreError):
    """Raised when a bounded operation (model call, tool call, transport) times out."""

    def __init__(self, message: str, *, operation: str | None = None) -> None:
        super().__init__(message)
        self.operation = operation
