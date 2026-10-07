"""Adapters from plugin capabilities to MCP-neutral definitions.

Business logic lives in plugins. This module only maps contracts.
"""

from __future__ import annotations

from collections.abc import Sequence

from ai_mcp_core.types import McpToolDefinition
from ai_plugins_sdk import ToolSpec


def tool_spec_to_mcp_definition(spec: ToolSpec) -> McpToolDefinition:
    return McpToolDefinition(
        name=spec.name,
        description=spec.description,
        inputSchema=dict(spec.input_schema),
    )


def tools_to_mcp_definitions(specs: Sequence[ToolSpec]) -> list[McpToolDefinition]:
    seen: set[str] = set()
    definitions: list[McpToolDefinition] = []
    for spec in specs:
        if spec.name in seen:
            raise ValueError(f"duplicate tool name: {spec.name!r}")
        seen.add(spec.name)
        definitions.append(tool_spec_to_mcp_definition(spec))
    return definitions
