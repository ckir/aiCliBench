import asyncio

from ai_core.errors import ValidationError
from ai_mcp_core import McpToolDefinition
from ai_mcp_testing import (
    assert_valid_tool_definition,
    check_discovery,
    check_malformed_inputs_rejected,
    check_unknown_tool_rejected,
    check_valid_invocation,
)


def _defs() -> list[McpToolDefinition]:
    return [
        McpToolDefinition(
            name="echo",
            description="Echo",
            inputSchema={"type": "object"},
        )
    ]


async def _call(name: str, args: dict[str, object]) -> dict[str, object]:
    if name != "echo":
        raise KeyError(name)
    if "text" not in args or not isinstance(args["text"], str):
        raise ValidationError("missing or invalid text")
    return {"text": args["text"]}


def test_mcp_testing_imports():
    import ai_mcp_testing

    assert ai_mcp_testing is not None


def test_harness_discovery_and_invocation():
    async def _run() -> None:
        defns = await check_discovery(_defs, expect_tools={"echo"})
        assert_valid_tool_definition(defns[0])
        result = await check_valid_invocation(_call, "echo", {"text": "hi"})
        assert result == {"text": "hi"}
        await check_malformed_inputs_rejected(_call, "echo", [{}, {"text": 1}])

    asyncio.run(_run())


def test_harness_unknown_tool():
    async def _run() -> None:
        await check_unknown_tool_rejected(_call)

    asyncio.run(_run())
