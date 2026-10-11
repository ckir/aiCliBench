"""Hidden acceptance tests for Token Bucket."""

from token_bucket import TokenBucket  # ty: ignore[unresolved-import]


def test_burst_and_refill():
    tb = TokenBucket(rate=10.0, capacity=20.0)
    t0 = 1000.0
    # Bucket starts full
    assert tb.available_tokens(now=t0) == 20.0
    assert tb.consume(tokens=15.0, now=t0) is True
    assert tb.available_tokens(now=t0) == 5.0

    # Cannot consume more than remaining
    assert tb.consume(tokens=10.0, now=t0) is False

    # After 1 second, 10 tokens are added: 5 + 10 = 15
    t1 = t0 + 1.0
    assert abs(tb.available_tokens(now=t1) - 15.0) < 1e-4
    assert tb.consume(tokens=15.0, now=t1) is True
    assert tb.available_tokens(now=t1) < 1e-4


def test_capacity_cap():
    tb = TokenBucket(rate=10.0, capacity=20.0)
    t0 = 1000.0
    tb.consume(20.0, now=t0)
    # After 10 seconds, tokens should cap at capacity 20, not 100
    t_later = t0 + 10.0
    assert tb.available_tokens(now=t_later) == 20.0
