"""Tool authorization policies. No model execution, no provider code."""

from __future__ import annotations

from typing import Protocol

from ai_plugins_sdk import ToolEffect, ToolSpec


class AuthorizationPolicy(Protocol):
    """Decides whether the agent may invoke a tool without further confirmation."""

    def is_authorized(self, spec: ToolSpec) -> bool: ...


class DefaultAuthorizationPolicy:
    """READ tools are allowed by default; WRITE/DESTRUCTIVE require opt-in.

    An explicit per-tool allowlist can override the effect defaults.
    """

    def __init__(
        self,
        *,
        allow_write: bool = False,
        allow_destructive: bool = False,
        allowed_tools: set[str] | None = None,
        denied_tools: set[str] | None = None,
    ) -> None:
        self._allow_write = allow_write
        self._allow_destructive = allow_destructive
        self._allowed = set(allowed_tools or ())
        self._denied = set(denied_tools or ())

    def is_authorized(self, spec: ToolSpec) -> bool:
        if spec.name in self._denied:
            return False
        if spec.name in self._allowed:
            return True
        if spec.effect is ToolEffect.READ:
            return True
        if spec.effect is ToolEffect.WRITE:
            return self._allow_write
        return self._allow_destructive
