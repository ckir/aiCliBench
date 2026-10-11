# Implement Memoization Decorator with TTL & Size Limit

In `memo_cache.py`, implement a caching decorator `memoize`.

### Requirements:
`def memoize(maxsize: int = 128, ttl_seconds: float | None = None) -> Callable`:
1. Caches return values of the decorated function based on arguments (`*args` and `**kwargs`).
2. `maxsize`: Maximum number of entries. When the cache exceeds `maxsize`, evicts the least recently used entry.
3. `ttl_seconds`: If provided, cached entries expire after `ttl_seconds`. Expired entries must be recomputed on subsequent calls.
4. Decorated function must provide utility methods and attributes:
   - `.cache_clear()`: Clears all cached entries.
   - `.cache_info()`: Returns a namedtuple or object with `hits`, `misses`, `currsize`, `maxsize`.
5. Supports `time_func: Callable[[], float]` parameter or uses `time.monotonic()`.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
