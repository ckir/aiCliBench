"""MCP server adapter: exposes plugin capabilities without owning business logic."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from ai_core.errors import (
    AiCoreError,
    AuthorizationError,
    ConfigurationError,
    OperationTimeoutError,
    ToolExecutionError,
    ValidationError,
)
from ai_mcp_core import McpToolDefinition, tool_spec_to_mcp_definition
from ai_mcp_server.validation import validate_args
from ai_plugins_sdk import Plugin, PluginRegistry


class McpServer:
    """Thin adapter over a :class:`PluginRegistry`.

    Responsibilities: discovery, argument validation, authorization gating,
    timeout bounding, and error normalization. Tool implementations live in
    plugins and are invoked unchanged.
    """

    def __init__(
        self,
        plugins: Sequence[Plugin] | PluginRegistry,
        *,
        timeout_seconds: float = 10.0,
    ) -> None:
        if isinstance(plugins, PluginRegistry):
            self._registry = plugins
        else:
            self._registry = PluginRegistry(list(plugins))
        if timeout_seconds <= 0:
            raise ConfigurationError("timeout_seconds must be positive")
        self._timeout_seconds = timeout_seconds

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    def list_tools(self) -> list[McpToolDefinition]:
        return [tool_spec_to_mcp_definition(spec) for spec in self._registry.tool_specs()]

    async def call_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        *,
        authorized: bool = False,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        entry = self._registry.get(tool_name)
        if entry is None:
            raise ConfigurationError(f"unknown tool: {tool_name!r}")
        plugin, spec = entry
        validate_args(args, spec.input_schema)
        if spec.requires_authorization and not authorized:
            raise AuthorizationError(
                f"tool {tool_name!r} requires explicit authorization",
                tool_name=tool_name,
            )
        timeout = timeout_seconds if timeout_seconds is not None else self._timeout_seconds
        try:
            result = await asyncio.wait_for(plugin.invoke(tool_name, dict(args)), timeout)
        except TimeoutError as exc:
            raise OperationTimeoutError(
                f"tool {tool_name!r} timed out after {timeout}s", operation="call_tool"
            ) from exc
        except (ValidationError, AuthorizationError, OperationTimeoutError):
            raise
        except ToolExecutionError:
            raise
        except AiCoreError as exc:
            raise ToolExecutionError(str(exc), tool_name=tool_name) from exc
        except Exception as exc:
            raise ToolExecutionError(f"tool {tool_name!r} failed", tool_name=tool_name) from exc
        if not isinstance(result, dict):
            raise ToolExecutionError(
                f"tool {tool_name!r} returned a non-object result", tool_name=tool_name
            )
        return result
