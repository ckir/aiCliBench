from lru_cache import LRUCache


def test_basic_put_get():
    cache = LRUCache(2)
    cache.put("a", 1)
    assert cache.get("a") == 1
    assert cache.get("nonexistent") is None
