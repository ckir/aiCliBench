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
        # Stub
        pass

    def unregister(self, name: str) -> bool:
        # Stub
        return False

    def get_plugins(self) -> list[Plugin]:
        # Stub
        return []

    def run_pipeline(self, data: dict) -> dict:
        # Stub
        return data
