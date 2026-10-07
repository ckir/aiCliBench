"""Deterministic example plugin (echo tool). Usable without MCP."""

from ai_plugin_example.plugin import ExamplePlugin
from ai_plugin_example.tools import EchoInput, EchoOutput, echo_text

__all__ = ["EchoInput", "EchoOutput", "ExamplePlugin", "echo_text"]
