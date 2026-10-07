import pytest

from ai_mcp_core import tool_spec_to_mcp_definition, tools_to_mcp_definitions
from ai_plugins_sdk import ToolSpec


def test_mcp_core_imports():
    import ai_mcp_core

    assert ai_mcp_core is not None


def test_tool_spec_to_definition():
    spec = ToolSpec(
        name="echo",
        description="Echo text",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
    )
    definition = tool_spec_to_mcp_definition(spec)
    assert definition.name == "echo"
    assert definition.inputSchema["type"] == "object"


def test_duplicate_names_rejected():
    specs = [
        ToolSpec(name="dup", description="a", input_schema={"type": "object"}),
        ToolSpec(name="dup", description="b", input_schema={"type": "object"}),
    ]
    with pytest.raises(ValueError, match="duplicate tool name"):
        tools_to_mcp_definitions(specs)
