import asyncio

from ai_mcp_client import InProcessMcpClient
from ai_mcp_core import McpToolDefinition


class _StubServer:
    def list_tools(self) -> list[McpToolDefinition]:
        return [McpToolDefinition(name="echo", description="Echo", inputSchema={"type": "object"})]

    async def call_tool(
        self, tool_name: str, args: dict[str, object], *, authorized: bool = False
    ) -> dict[str, object]:
        assert tool_name == "echo"
        return {"echo": True, "authorized": authorized}


def test_mcp_client_imports():
    import ai_mcp_client

    assert ai_mcp_client is not None


def test_in_process_client_delegates():
    async def _run() -> None:
        client = InProcessMcpClient(_StubServer())  # type: ignore[arg-type]
        tools = await client.list_tools()
        assert [t.name for t in tools] == ["echo"]
        result = await client.call_tool("echo", {}, authorized=True)
        assert result == {"echo": True, "authorized": True}

    asyncio.run(_run())


def test_in_process_client_default_authorized_flag():
    async def _run() -> None:
        client = InProcessMcpClient(_StubServer(), authorized=True)  # type: ignore[arg-type]
        result = await client.call_tool("echo", {})
        assert result["authorized"] is True

    asyncio.run(_run())
