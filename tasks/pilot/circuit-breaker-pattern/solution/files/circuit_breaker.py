"""Circuit Breaker Pattern."""

import time
from collections.abc import Callable
from typing import Any


class CircuitBreakerOpenException(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 10.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = "CLOSED"
        self._failure_count = 0
        self._opened_at = 0.0

    @property
    def state(self) -> str:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def call(self, func: Callable, *args: Any, now: float | None = None, **kwargs: Any) -> Any:
        current = time.time() if now is None else now
        if self._state == "OPEN":
            if current - self._opened_at >= self.recovery_timeout:
                self._state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenException("circuit is open")
        try:
            result = func(*args, **kwargs)
        except Exception:
            self._failure_count += 1
            if self._state == "HALF_OPEN" or self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
                self._opened_at = current
            raise
        self._failure_count = 0
        self._state = "CLOSED"
        return result
