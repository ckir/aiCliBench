"""Hidden acceptance tests for memoize."""

from memo_cache import memoize  # ty: ignore[unresolved-import]


def test_cache_hits_and_misses():
    calls = 0

    @memoize(maxsize=10)
    def compute(a, b):
        nonlocal calls
        calls += 1
        return a + b

    assert compute(2, 3) == 5
    assert calls == 1
    assert compute(2, 3) == 5
    assert calls == 1  # Cache hit!

    info = compute.cache_info()
    assert info.hits == 1
    assert info.misses == 1


def test_cache_clear():
    calls = 0

    @memoize(maxsize=10)
    def f(x):
        nonlocal calls
        calls += 1
        return x * 2

    f(1)
    f.cache_clear()
    f(1)
    assert calls == 2
