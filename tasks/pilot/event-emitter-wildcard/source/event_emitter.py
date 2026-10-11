"""Wildcard event emitter."""

from collections.abc import Callable
from typing import Any


class EventEmitter:
    def __init__(self) -> None:
        self._listeners: list[tuple[str, Callable, bool]] = []

    def on(self, pattern: str, handler: Callable) -> None:
        self._listeners.append((pattern, handler, False))

    def once(self, pattern: str, handler: Callable) -> None:
        self._listeners.append((pattern, handler, True))

    def off(self, pattern: str, handler: Callable) -> bool:
        # Stub
        return False

    def emit(self, event: str, *args: Any, **kwargs: Any) -> int:
        # Stub
        return 0
