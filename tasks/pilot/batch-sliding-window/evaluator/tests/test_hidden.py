"""Hidden acceptance tests for SlidingWindowStats."""

import time

from sliding_window import SlidingWindowStats  # ty: ignore[unresolved-import]


def test_large_stream_performance():
    W = 1000
    sw = SlidingWindowStats(W)
    N = 20000

    start = time.perf_counter()
    for i in range(N):
        sw.push(float(i % 100))
        if i >= W:
            _ = sw.get_min()
            _ = sw.get_max()
            _ = sw.get_mean()
    elapsed = time.perf_counter() - start

    assert elapsed < 0.25, f"Sliding window operations too slow: {elapsed:.3f}s"


def test_window_eviction_correctness():
    sw = SlidingWindowStats(3)
    sw.push(100)
    sw.push(5)
    sw.push(50)
    assert sw.get_min() == 5
    assert sw.get_max() == 100

    # 100 is evicted
    sw.push(20)
    assert sw.get_max() == 50
    assert sw.get_min() == 5
