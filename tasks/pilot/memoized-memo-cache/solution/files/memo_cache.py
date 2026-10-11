"""Memoization decorator."""

import functools
import time
from collections import OrderedDict, namedtuple
from collections.abc import Callable
from typing import Any

CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "currsize", "maxsize"])


def memoize(
    maxsize: int = 128,
    ttl_seconds: float | None = None,
    time_func: Callable[[], float] | None = None,
) -> Callable:
    clock = time_func if time_func is not None else time.monotonic

    def decorator(fn: Callable) -> Callable:
        # key -> (result, timestamp)
        cache: OrderedDict[Any, tuple[Any, float]] = OrderedDict()
        hits = 0
        misses = 0

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal hits, misses
            key = (args, tuple(sorted(kwargs.items())))
            now = clock()
            entry = cache.get(key)
            if entry is not None:
                result, stamp = entry
                if ttl_seconds is None or now - stamp < ttl_seconds:
                    cache.move_to_end(key)
                    hits += 1
                    return result
                del cache[key]
            misses += 1
            result = fn(*args, **kwargs)
            cache[key] = (result, now)
            cache.move_to_end(key)
            while len(cache) > maxsize:
                cache.popitem(last=False)
            return result

        def cache_clear() -> None:
            nonlocal hits, misses
            cache.clear()
            hits = 0
            misses = 0

        def cache_info() -> CacheInfo:
            return CacheInfo(hits, misses, len(cache), maxsize)

        wrapper.cache_clear = cache_clear  # ty: ignore[unresolved-attribute]
        wrapper.cache_info = cache_info  # ty: ignore[unresolved-attribute]
        return wrapper

    return decorator
