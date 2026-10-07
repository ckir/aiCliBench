"""Plugin and tool contracts. Keep minimal and provider-independent."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class ToolEffect(StrEnum):
    """Side-effect classification. Write/destructive tools require explicit authorization."""

    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Stable, transport-independent capability description."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    effect: ToolEffect = ToolEffect.READ

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("tool name must be non-empty")
        if not self.description or not self.description.strip():
            raise ValueError("tool description must be non-empty")
        if not isinstance(self.input_schema, dict) or not self.input_schema:
            raise ValueError("input_schema must be a non-empty dict")

    @property
    def requires_authorization(self) -> bool:
        """Write/destructive tools must be authorized by the caller/runtime."""
        return self.effect in (ToolEffect.WRITE, ToolEffect.DESTRUCTIVE)


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    name: str
    version: str
    description: str
    config_schema: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("plugin name must be non-empty")


class Plugin(Protocol):
    """Minimal plugin contract. Usable without MCP, HTTP, or an agent runtime."""

    @property
    def metadata(self) -> PluginMetadata: ...

    def tools(self) -> Sequence[ToolSpec]: ...

    async def invoke(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool with already-decoded JSON-compatible arguments."""
        ...


class AsyncLifecycle(Protocol):
    """Optional lifecycle hooks. Implement only when genuinely necessary."""

    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
