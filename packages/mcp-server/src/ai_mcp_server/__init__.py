"""Reusable MCP server adapter over plugin capabilities."""

from ai_mcp_server.server import McpServer
from ai_mcp_server.validation import validate_args

__all__ = ["McpServer", "validate_args"]
