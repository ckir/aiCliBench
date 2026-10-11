"""Wildcard event emitter."""

import re
from collections.abc import Callable
from typing import Any


def _pattern_to_regex(pattern: str) -> re.Pattern[str]:
    regex_parts = []
    for part in pattern.split("."):
        if part == "**":
            regex_parts.append(r".*")
        elif part == "*":
            regex_parts.append(r"[^.]+")
        else:
            regex_parts.append(re.escape(part))
    return re.compile("^" + r"\.".join(regex_parts) + "$")


class EventEmitter:
    def __init__(self) -> None:
        self._listeners: list[tuple[str, Callable, bool]] = []

    def on(self, pattern: str, handler: Callable) -> None:
        self._listeners.append((pattern, handler, False))

    def once(self, pattern: str, handler: Callable) -> None:
        self._listeners.append((pattern, handler, True))

    def off(self, pattern: str, handler: Callable) -> bool:
        for i, (pat, fn, _) in enumerate(self._listeners):
            if pat == pattern and fn == handler:
                del self._listeners[i]
                return True
        return False

    def emit(self, event: str, *args: Any, **kwargs: Any) -> int:
        matched = [entry for entry in self._listeners if _pattern_to_regex(entry[0]).match(event)]
        for entry in matched:
            if entry[2]:
                self._listeners.remove(entry)
        for _, fn, _ in matched:
            fn(*args, **kwargs)
        return len(matched)
