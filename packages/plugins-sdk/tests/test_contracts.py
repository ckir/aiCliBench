import pytest

from ai_plugins_sdk import PluginMetadata, PluginRegistry, ToolEffect, ToolSpec


def test_tool_spec_defaults_to_read():
    spec = ToolSpec(
        name="example",
        description="Example tool",
        input_schema={"type": "object"},
    )

    assert spec.effect is ToolEffect.READ
    assert not spec.requires_authorization


def test_write_requires_authorization():
    spec = ToolSpec(
        name="write_thing",
        description="Writes",
        input_schema={"type": "object"},
        effect=ToolEffect.WRITE,
    )
    assert spec.requires_authorization

    destructive = ToolSpec(
        name="delete_thing",
        description="Deletes",
        input_schema={"type": "object"},
        effect=ToolEffect.DESTRUCTIVE,
    )
    assert destructive.requires_authorization


def test_tool_spec_rejects_empty_name():
    with pytest.raises(ValueError, match="tool name"):
        ToolSpec(name="", description="x", input_schema={"type": "object"})


def test_registry_rejects_duplicate_tools():
    from ai_core.errors import ConfigurationError

    class _Plugin:
        def __init__(self, plugin_name: str, tool_name: str) -> None:
            self._meta = PluginMetadata(name=plugin_name, version="0.1.0", description="test")
            self._tool = ToolSpec(name=tool_name, description="t", input_schema={"type": "object"})

        @property
        def metadata(self) -> PluginMetadata:
            return self._meta

        def tools(self) -> list[ToolSpec]:
            return [self._tool]

        async def invoke(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
            return {}

    registry = PluginRegistry([_Plugin("a", "dup")])  # type: ignore[list-item]
    with pytest.raises(ConfigurationError):
        registry.register(_Plugin("b", "dup"))  # type: ignore[arg-type]
