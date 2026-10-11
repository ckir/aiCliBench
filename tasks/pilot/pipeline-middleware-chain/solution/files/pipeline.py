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
        def dispatch(index: int, ctx: dict) -> dict:
            if index == len(self._middlewares):
                return ctx
            mw = self._middlewares[index]
            return mw(ctx, lambda next_ctx: dispatch(index + 1, next_ctx))

        return dispatch(0, dict(context))
