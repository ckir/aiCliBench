import asyncio
from typing import Any

from ai_agents import (
    AgentConfig,
    DefaultAuthorizationPolicy,
    run_agent,
    to_model_tools,
)
from ai_core.errors import ConfigurationError
from ai_plugins_sdk import PluginMetadata, ToolEffect, ToolSpec
from ai_runtime import FakeChatModel


class _EchoPlugin:
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="echo", version="0.1.0", description="echo")

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="echo",
                description="Echo",
                input_schema={"type": "object"},
                effect=ToolEffect.READ,
            )
        ]

    async def invoke(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"text": args.get("text", ""), "length": len(str(args.get("text", "")))}


class _WriterPlugin:
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="writer", version="0.1.0", description="writer")

    def tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="overwrite",
                description="Write",
                input_schema={"type": "object"},
                effect=ToolEffect.WRITE,
            )
        ]

    async def invoke(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True}


def test_agents_package_imports():
    import ai_agents

    assert ai_agents is not None


def test_agent_answers_without_tools():
    async def _run() -> None:
        model = FakeChatModel(responses=[FakeChatModel.text("done")])
        result = await run_agent(model, [_EchoPlugin()], "hi")  # type: ignore[list-item]
        assert result.answer == "done"
        assert result.completed is True
        assert result.tool_calls == 0

    asyncio.run(_run())


def test_agent_uses_echo_tool_then_answers():
    async def _run() -> None:
        model = FakeChatModel(
            responses=[
                FakeChatModel.tool("echo", {"text": "hi"}),
                FakeChatModel.text("you said hi"),
            ]
        )
        result = await run_agent(model, [_EchoPlugin()], "say hi")  # type: ignore[list-item]
        assert result.tool_calls == 1
        assert result.answer == "you said hi"
        # The tool output must have been fed back to the model.
        second_call_messages = model.calls[1].messages
        assert any(m.role == "tool" and "hi" in m.content for m in second_call_messages)

    asyncio.run(_run())


def test_agent_denies_write_by_default():
    async def _run() -> None:
        model = FakeChatModel(
            responses=[
                FakeChatModel.tool("overwrite", {}),
                FakeChatModel.text("blocked?"),
            ]
        )
        result = await run_agent(model, [_WriterPlugin()], "write it")  # type: ignore[list-item]
        assert result.completed is True
        tool_feedback = model.calls[1].messages
        assert any("not authorized" in m.content for m in tool_feedback if m.role == "tool")

    asyncio.run(_run())


def test_agent_allows_write_with_policy():
    async def _run() -> None:
        model = FakeChatModel(
            responses=[
                FakeChatModel.tool("overwrite", {}),
                FakeChatModel.text("written"),
            ]
        )
        policy = DefaultAuthorizationPolicy(allow_write=True)
        result = await run_agent(
            model,
            [_WriterPlugin()],
            "write",
            policy=policy,  # type: ignore[list-item]
        )
        assert result.answer == "written"

    asyncio.run(_run())


def test_agent_budget_exhaustion():
    async def _run() -> None:
        model = FakeChatModel(
            responses=[
                FakeChatModel.tool("echo", {"text": "a"}),
                FakeChatModel.tool("echo", {"text": "b"}),
                FakeChatModel.text("late"),
            ]
        )
        result = await run_agent(
            model,
            [_EchoPlugin()],  # type: ignore[list-item]
            "loop",
            config=AgentConfig(max_steps=1),
        )
        assert result.completed is False

    asyncio.run(_run())


def test_agent_config_validation():
    try:
        AgentConfig(max_steps=0)
    except ConfigurationError:
        pass
    else:
        raise AssertionError("expected ConfigurationError")


def test_to_model_tools_shape():
    specs = _EchoPlugin().tools()
    tools = to_model_tools(specs)
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "echo"
