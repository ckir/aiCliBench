"""MCP-neutral tool/result contracts (Pydantic v2, JSON-compatible)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class McpToolDefinition(BaseModel):
    """Transport-neutral MCP tool description derived from a ``ToolSpec``."""

    model_config = {"extra": "forbid"}

    name: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1)
    inputSchema: dict[str, Any]


class McpCallResult(BaseModel):
    """Structured tool result. ``isError`` mirrors the MCP content convention."""

    model_config = {"extra": "forbid"}

    output: dict[str, Any] = Field(default_factory=dict)
    isError: bool = False
    error: str | None = None
