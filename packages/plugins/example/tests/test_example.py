import asyncio

import pytest

from ai_core.errors import ValidationError
from ai_plugin_example import ExamplePlugin, echo_text
from ai_plugins_sdk import PluginRegistry, ToolEffect


def test_example_plugin_direct_use():
    out = echo_text("hello")
    assert out.text == "hello"
    assert out.length == 5


def test_example_plugin_contract():
    plugin = ExamplePlugin()
    assert plugin.metadata.name == "example"
    specs = plugin.tools()
    assert len(specs) == 1
    assert specs[0].name == "echo"
    assert specs[0].effect is ToolEffect.READ
    assert not specs[0].requires_authorization


def test_example_plugin_invoke():
    async def _run() -> None:
        plugin = ExamplePlugin()
        result = await plugin.invoke("echo", {"text": "hi"})
        assert result == {"text": "hi", "length": 2}

    asyncio.run(_run())


def test_example_plugin_rejects_bad_input():
    async def _run() -> None:
        plugin = ExamplePlugin()
        with pytest.raises(ValidationError):
            await plugin.invoke("echo", {})
        with pytest.raises(ValidationError):
            await plugin.invoke("echo", {"text": ""})

    asyncio.run(_run())


def test_example_plugin_via_registry():
    async def _run() -> None:
        registry = PluginRegistry([ExamplePlugin()])  # type: ignore[list-item]
        result = await registry.invoke("echo", {"text": "abc"})
        assert result == {"text": "abc", "length": 3}

    asyncio.run(_run())
