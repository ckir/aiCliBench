"""Circuit Breaker Pattern."""

from collections.abc import Callable
from typing import Any


class CircuitBreakerOpenException(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 10.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        # Stub
        self._state = "CLOSED"
        self._failure_count = 0

    @property
    def state(self) -> str:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def call(self, func: Callable, *args: Any, now: float | None = None, **kwargs: Any) -> Any:
        # Stub
        return func(*args, **kwargs)
