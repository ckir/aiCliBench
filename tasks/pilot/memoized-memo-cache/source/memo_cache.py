"""Memoization decorator."""

import functools
from collections.abc import Callable
from typing import Any


def memoize(maxsize: int = 128, ttl_seconds: float | None = None) -> Callable:
    # Incomplete stub
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        return wrapper

    return decorator
