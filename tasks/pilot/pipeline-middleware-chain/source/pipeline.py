"""Middleware Pipeline."""

from __future__ import annotations

from collections.abc import Callable


class Pipeline:
    def __init__(self) -> None:
        self._middlewares: list[Callable] = []

    def use(self, middleware: Callable) -> Pipeline:
        self._middlewares.append(middleware)
        return self

    def execute(self, context: dict) -> dict:
        # Stub
        return context
