from token_bucket import TokenBucket


def test_init_validation():
    tb = TokenBucket(10.0, 20.0)
    assert tb.capacity == 20.0
    assert tb.rate == 10.0
