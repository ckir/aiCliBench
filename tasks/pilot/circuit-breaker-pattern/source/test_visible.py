from circuit_breaker import CircuitBreaker


def test_initial_state():
    cb = CircuitBreaker()
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0
