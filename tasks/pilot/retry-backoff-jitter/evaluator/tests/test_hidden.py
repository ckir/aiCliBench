"""Hidden acceptance tests for compute_backoff."""

from retry import compute_backoff  # ty: ignore[unresolved-import]


def test_jitter_never_negative_or_exceeds_max():
    for attempt in range(10):
        for _ in range(50):
            d = compute_backoff(attempt, base_delay=0.5, max_delay=10.0, jitter=True)
            max_possible = min(10.0, 0.5 * (2**attempt))
            assert 0.0 <= d <= max_possible


def test_deterministic_cap():
    val = compute_backoff(10, base_delay=1.0, max_delay=15.0, jitter=False)
    assert val == 15.0
