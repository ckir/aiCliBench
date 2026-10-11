"""Explicit result type for fallible domain operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ai_core.errors import AiCoreError


@dataclass(frozen=True, slots=True)
class Result[T]:
    """A minimal explicit result container.

    Prefer raising typed exceptions at boundaries (see ``errors``) and use
    ``Result`` only where the caller is expected to branch on failure as data.

    Attributes:
        value: The success value, or ``None`` if an error occurred.
        error: The error if the operation failed, ``None`` otherwise.
    """

    value: T | None = None
    error: AiCoreError | None = None

    @property
    def is_ok(self) -> bool:
        """Return ``True`` if the result contains a value (no error)."""
        return self.error is None

    def unwrap(self) -> T:
        """Return the contained value or raise the contained error.

        Raises:
            AiCoreError: If the result contains an error.
        """
        if self.error is not None:
            raise self.error
        # ``value`` may legitimately be None for ``Result[None]``.
        return cast(T, self.value)
