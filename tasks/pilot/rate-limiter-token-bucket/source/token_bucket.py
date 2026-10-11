"""Token Bucket Rate Limiter."""

from __future__ import annotations

import time


class TokenBucket:
    def __init__(self, rate: float, capacity: float) -> None:
        if rate <= 0 or capacity <= 0:
            raise ValueError("rate and capacity must be positive")
        self.rate = rate
        self.capacity = capacity
        # INCOMPLETE SKELETON
        self._tokens = capacity
        self._last_time = time.time()

    def available_tokens(self, now: float | None = None) -> float:
        # Stub
        return self._tokens

    def consume(self, tokens: float = 1.0, now: float | None = None) -> bool:
        # Stub
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        return False
