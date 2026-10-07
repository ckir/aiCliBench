import asyncio
from typing import Any

import pytest

from ai_core.errors import (
    AuthorizationError,
    ConfigurationError,
    OperationTimeoutError,
    ToolExecutionError,
    ValidationError,
)
from ai_mcp_server import McpServer
from ai_mcp_testing import (
    check_discovery,
    check_malformed_inputs_rejected,
    check_unknown_tool_rejected,
    check_valid_invocation,
)
from ai_plugins_sdk import PluginMetadata, ToolEffect, ToolSpec


class _EchoPlugin:
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="echo-plugin", version="0.1.0", description="test")

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="echo",
                description="Echo text",
                input_schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
                output_schema={"type": "object"},
                effect=ToolEffect.READ,
            ),
            ToolSpec(
                name="overwrite",
                description="Write path",
                input_schema={"type": "object"},
                effect=ToolEffect.WRITE,
            ),
        ]

    async def invoke(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "echo":
            text = args["text"]
            assert isinstance(text, str)
            return {"text": text}
        if tool_name == "overwrite":
            return {"ok": True}
        raise ConfigurationError(f"unknown tool {tool_name!r}")


class _FailingPlugin:
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="fail", version="0.1.0", description="fail")

    def tools(self) -> list[ToolSpec]:
        return [ToolSpec(name="boom", description="Always fails", input_schema={"type": "object"})]

    async def invoke(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("downstream exploded")


class _SlowPlugin:
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="slow", version="0.1.0", description="slow")

    def tools(self) -> list[ToolSpec]:
        return [ToolSpec(name="slow", description="Slow tool", input_schema={"type": "object"})]

    async def invoke(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(5)
        return {}


def test_mcp_server_imports():
    import ai_mcp_server

    assert ai_mcp_server is not None


def test_discovery_via_harness():
    async def _run() -> None:
        server = McpServer([_EchoPlugin()])  # type: ignore[list-item]
        await check_discovery(server.list_tools, expect_tools={"echo", "overwrite"})

    asyncio.run(_run())


def test_valid_invocation_via_harness():
    async def _run() -> None:
        server = McpServer([_EchoPlugin()])  # type: ignore[list-item]
        result = await check_valid_invocation(server.call_tool, "echo", {"text": "hi"})
        assert result == {"text": "hi"}

    asyncio.run(_run())


def test_malformed_and_unknown_via_harness():
    async def _run() -> None:
        server = McpServer([_EchoPlugin()])  # type: ignore[list-item]
        await check_malformed_inputs_rejected(
            server.call_tool, "echo", [{}, {"text": 1}, {"text": "x", "extra": 1}]
        )
        await check_unknown_tool_rejected(server.call_tool)

    asyncio.run(_run())


def test_authorization_rejection():
    async def _run() -> None:
        server = McpServer([_EchoPlugin()])  # type: ignore[list-item]
        with pytest.raises(AuthorizationError):
            await server.call_tool("overwrite", {}, authorized=False)
        result = await server.call_tool("overwrite", {}, authorized=True)
        assert result == {"ok": True}

    asyncio.run(_run())


def test_downstream_failure_normalized():
    async def _run() -> None:
        server = McpServer([_FailingPlugin()])  # type: ignore[list-item]
        with pytest.raises(ToolExecutionError):
            await server.call_tool("boom", {})

    asyncio.run(_run())


def test_timeout_behavior():
    async def _run() -> None:
        server = McpServer([_SlowPlugin()], timeout_seconds=0.05)  # type: ignore[list-item]
        with pytest.raises(OperationTimeoutError):
            await server.call_tool("slow", {})

    asyncio.run(_run())


def test_invalid_timeout_config():
    from typing import Any

    with pytest.raises(ConfigurationError):
        McpServer([], timeout_seconds=0)

    async def _run() -> None:
        server = McpServer([_EchoPlugin()])  # type: ignore[list-item]
        bad_args: Any = "not-a-dict"
        with pytest.raises(ValidationError):
            await server.call_tool("echo", bad_args)

    asyncio.run(_run())
