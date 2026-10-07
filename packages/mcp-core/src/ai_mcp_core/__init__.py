"""MCP-neutral contracts and adapters (no transport, no business logic)."""

from ai_mcp_core.adapters import tool_spec_to_mcp_definition, tools_to_mcp_definitions
from ai_mcp_core.types import McpCallResult, McpToolDefinition

__all__ = [
    "McpCallResult",
    "McpToolDefinition",
    "tool_spec_to_mcp_definition",
    "tools_to_mcp_definitions",
]
