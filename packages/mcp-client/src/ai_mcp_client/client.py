"""Client abstraction for connecting to MCP servers.

Transport details (in-process, stdio, SSE, HTTP) stay behind the
:class:`McpClient` interface. Business logic never depends on a concrete
transport.
"""

from __future__ import annotations

from typing import Any, Protocol

from ai_mcp_core import McpToolDefinition


class McpClient(Protocol):
    """Minimal client interface used by agents and services."""

    async def list_tools(self) -> list[McpToolDefinition]: ...

    async def call_tool(
        self, tool_name: str, args: dict[str, Any], *, authorized: bool = False
    ) -> dict[str, Any]: ...


class ServerLike(Protocol):
    """Structural type for an in-process server. Avoids a hard mcp-server dependency."""

    def list_tools(self) -> list[McpToolDefinition]: ...

    async def call_tool(
        self, tool_name: str, args: dict[str, Any], *, authorized: bool = False
    ) -> dict[str, Any]: ...


class InProcessMcpClient:
    """Delegates to an in-process server object. Ideal for tests and single-process services."""

    def __init__(self, server: ServerLike, *, authorized: bool = False) -> None:
        self._server = server
        self._authorized = authorized

    async def list_tools(self) -> list[McpToolDefinition]:
        result = self._server.list_tools()
        if isinstance(result, list):
            return result
        return await result  # type: ignore[no-any-return]

    async def call_tool(
        self, tool_name: str, args: dict[str, Any], *, authorized: bool | None = None
    ) -> dict[str, Any]:
        flag = self._authorized if authorized is None else authorized
        return await self._server.call_tool(tool_name, dict(args), authorized=flag)
