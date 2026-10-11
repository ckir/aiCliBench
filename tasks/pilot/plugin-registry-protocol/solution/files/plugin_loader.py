"""Protocol-based Plugin Loader."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Plugin(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def priority(self) -> int: ...

    def process(self, data: dict) -> dict: ...


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Any) -> None:
        if not isinstance(plugin, Plugin):
            raise TypeError("plugin does not conform to the Plugin protocol")
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin already registered: {plugin.name}")
        self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> bool:
        return self._plugins.pop(name, None) is not None

    def get_plugins(self) -> list[Plugin]:
        return sorted(self._plugins.values(), key=lambda p: p.priority)

    def run_pipeline(self, data: dict) -> dict:
        for plugin in self.get_plugins():
            data = plugin.process(data)
        return data
