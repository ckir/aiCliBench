"""Reusable MCP test harness: discovery, schema, invocation, malformed input.

The harness is transport-independent. It operates on two callables so the same
checks apply to an in-process server, an HTTP gateway, or a remote MCP server
behind a thin client adapter.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from ai_core.errors import AiCoreError
from ai_mcp_core import McpToolDefinition

ListTools = Callable[[], list[McpToolDefinition] | Awaitable[list[McpToolDefinition]]]
CallTool = Callable[[str, dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]


def assert_valid_tool_definition(defn: McpToolDefinition) -> None:
    if not defn.name or not defn.name.strip():
        raise ValueError("tool name must be non-empty")
    if not defn.description or not defn.description.strip():
        raise ValueError("tool description required")
    if not isinstance(defn.inputSchema, dict):
        raise ValueError("inputSchema must be a dict")
    if defn.inputSchema.get("type") != "object":
        raise ValueError("inputSchema must be an object schema")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def check_discovery(
    list_tools: ListTools,
    *,
    expect_tools: set[str] | None = None,
) -> list[McpToolDefinition]:
    defns = await _maybe_await(list_tools())
    if not isinstance(defns, list):
        raise AssertionError("expected tool list")
    if not defns:
        raise AssertionError("expected at least one tool")
    names = [d.name for d in defns]
    if len(names) != len(set(names)):
        raise AssertionError(f"duplicate tool names: {names}")
    for d in defns:
        assert_valid_tool_definition(d)
    if expect_tools is not None:
        missing = expect_tools - set(names)
        if missing:
            raise AssertionError(f"missing expected tools: {missing}")
    return defns


async def check_valid_invocation(
    call_tool: CallTool,
    tool_name: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    result = await _maybe_await(call_tool(tool_name, args))
    if not isinstance(result, dict):
        raise AssertionError("tool result must be a JSON-compatible dict")
    return result


async def check_malformed_inputs_rejected(
    call_tool: CallTool,
    tool_name: str,
    bad_args: list[dict[str, Any]],
) -> None:
    for args in bad_args:
        try:
            await _maybe_await(call_tool(tool_name, args))
        except (AiCoreError, ValueError):
            continue
        raise AssertionError(f"expected rejection for args={args!r}")


async def check_unknown_tool_rejected(call_tool: CallTool) -> None:
    try:
        await _maybe_await(call_tool("__no_such_tool__", {}))
    except (AiCoreError, ValueError, KeyError):
        return
    raise AssertionError("expected rejection for unknown tool")
