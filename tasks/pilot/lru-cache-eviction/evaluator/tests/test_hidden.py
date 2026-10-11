"""Hidden acceptance tests for LRU Cache."""

from lru_cache import LRUCache  # ty: ignore[unresolved-import]


def test_get_updates_recency():
    cache = LRUCache(2)
    cache.put(1, "one")
    cache.put(2, "two")
    # Access key 1; key 2 is now least recently used
    assert cache.get(1) == "one"
    # Insert key 3; key 2 should be evicted, not key 1
    cache.put(3, "three")
    assert cache.get(1) == "one"
    assert cache.get(2) is None
    assert cache.get(3) == "three"


def test_put_update_updates_recency():
    cache = LRUCache(2)
    cache.put("a", 10)
    cache.put("b", 20)
    # Updating 'a' makes 'b' least recently used
    cache.put("a", 100)
    cache.put("c", 30)
    assert cache.get("a") == 100
    assert cache.get("b") is None
    assert cache.get("c") == 30
