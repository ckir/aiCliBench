from retry import compute_backoff


def test_without_jitter():
    val = compute_backoff(2, base_delay=1.0, max_delay=60.0, jitter=False)
    assert val == 4.0
