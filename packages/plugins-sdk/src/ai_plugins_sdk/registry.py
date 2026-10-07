"""In-memory plugin registry with duplicate-tool detection."""

from __future__ import annotations

from ai_core.errors import ConfigurationError
from ai_plugins_sdk.contracts import Plugin, ToolSpec


class PluginRegistry:
    """Collects plugins and exposes a unified, stable tool namespace."""

    def __init__(self, plugins: list[Plugin] | None = None) -> None:
        self._plugins: list[Plugin] = list(plugins) if plugins else []
        self._tools: dict[str, tuple[Plugin, ToolSpec]] = {}
        for plugin in self._plugins:
            self._register_plugin_tools(plugin)

    def register(self, plugin: Plugin) -> None:
        self._register_plugin_tools(plugin)
        self._plugins.append(plugin)

    def _register_plugin_tools(self, plugin: Plugin) -> None:
        for spec in plugin.tools():
            if spec.name in self._tools:
                existing_plugin, _ = self._tools[spec.name]
                raise ConfigurationError(
                    f"duplicate tool name {spec.name!r}: "
                    f"{existing_plugin.metadata.name!r} vs {plugin.metadata.name!r}"
                )
            self._tools[spec.name] = (plugin, spec)

    @property
    def plugins(self) -> list[Plugin]:
        return list(self._plugins)

    def tool_specs(self) -> list[ToolSpec]:
        return [spec for _, spec in self._tools.values()]

    def get(self, tool_name: str) -> tuple[Plugin, ToolSpec] | None:
        return self._tools.get(tool_name)

    async def invoke(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        entry = self._tools.get(tool_name)
        if entry is None:
            raise ConfigurationError(f"unknown tool: {tool_name!r}")
        plugin, _ = entry
        return await plugin.invoke(tool_name, dict(args))
