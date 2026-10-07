"""Example plugin exposing the ``echo`` tool."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ai_core.errors import ConfigurationError, ValidationError
from ai_plugin_example.tools import EchoInput, EchoOutput, echo_text
from ai_plugins_sdk import PluginMetadata, ToolEffect, ToolSpec

_TOOL_NAME = "echo"


class ExamplePlugin:
    """Minimal, independently usable plugin. No MCP dependency."""

    def __init__(self) -> None:
        self._metadata = PluginMetadata(
            name="example",
            version="0.1.0",
            description="Deterministic example plugin (echo tool).",
        )
        input_schema = EchoInput.model_json_schema()
        input_schema.setdefault("type", "object")
        output_schema = EchoOutput.model_json_schema()
        output_schema.setdefault("type", "object")
        self._tools = [
            ToolSpec(
                name=_TOOL_NAME,
                description="Echo text back with its character length.",
                input_schema=input_schema,
                output_schema=output_schema,
                effect=ToolEffect.READ,
            )
        ]

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def tools(self) -> Sequence[ToolSpec]:
        return list(self._tools)

    async def invoke(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool_name != _TOOL_NAME:
            raise ConfigurationError(f"unknown tool: {tool_name!r}")
        try:
            validated = EchoInput.model_validate(args)
        except Exception as exc:
            raise ValidationError(f"invalid arguments for {_TOOL_NAME!r}: {exc}") from exc
        return echo_text(validated.text).model_dump()
