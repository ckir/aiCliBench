# Fix LRU Cache item access recency

In `lru_cache.py`, the `LRUCache` class is intended to implement a Least Recently Used eviction policy with fixed capacity.

Currently, calling `get(key)` returns the value correctly, but fails to mark the accessed item as recently used. Consequently, when a new item is inserted and capacity is exceeded, an item that was recently accessed with `get()` may be incorrectly evicted instead of the actual least-recently-used item.

Fix `lru_cache.py` so that:
1. `get(key)` marks the item as most recently used.
2. `put(key, value)` updates existing keys and marks them as most recently used.
3. Eviction always removes the least recently used item when capacity is exceeded.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
