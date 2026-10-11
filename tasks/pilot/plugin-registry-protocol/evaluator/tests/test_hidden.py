"""Hidden acceptance tests for PluginRegistry."""

import pytest
from plugin_loader import PluginRegistry  # ty: ignore[unresolved-import]


class Normalizer:
    @property
    def name(self) -> str:
        return "normalizer"

    @property
    def priority(self) -> int:
        return 10

    def process(self, data: dict) -> dict:
        data["text"] = data["text"].strip().lower()
        return data


class Appender:
    @property
    def name(self) -> str:
        return "appender"

    @property
    def priority(self) -> int:
        return 20

    def process(self, data: dict) -> dict:
        data["text"] += "!"
        return data


def test_protocol_validation_and_pipeline():
    reg = PluginRegistry()
    p1 = Normalizer()
    p2 = Appender()

    reg.register(p2)
    reg.register(p1)

    plugins = reg.get_plugins()
    assert [p.name for p in plugins] == ["normalizer", "appender"]

    res = reg.run_pipeline({"text": "  Hello World  "})
    assert res == {"text": "hello world!"}


def test_type_error_for_invalid_plugin():
    reg = PluginRegistry()
    with pytest.raises(TypeError):
        reg.register(object())
