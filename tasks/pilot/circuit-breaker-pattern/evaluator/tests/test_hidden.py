"""Hidden acceptance tests for Circuit Breaker."""

import pytest
from circuit_breaker import (  # ty: ignore[unresolved-import]
    CircuitBreaker,
    CircuitBreakerOpenException,
)


def test_transition_closed_to_open():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)

    def failing():
        raise RuntimeError("network down")

    t0 = 1000.0
    with pytest.raises(RuntimeError):
        cb.call(failing, now=t0)
    assert cb.state == "CLOSED"
    assert cb.failure_count == 1

    with pytest.raises(RuntimeError):
        cb.call(failing, now=t0)
    assert cb.state == "OPEN"

    # Immediately blocked
    with pytest.raises(CircuitBreakerOpenException):
        cb.call(lambda: "ok", now=t0 + 1.0)


def test_transition_open_to_half_open_to_closed():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5.0)
    t0 = 1000.0
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")), now=t0)
    assert cb.state == "OPEN"

    # Before timeout: remains OPEN
    with pytest.raises(CircuitBreakerOpenException):
        cb.call(lambda: "ok", now=t0 + 4.9)

    # After timeout: transitions to HALF_OPEN and allows test call
    res = cb.call(lambda: "recovered", now=t0 + 5.1)
    assert res == "recovered"
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0
