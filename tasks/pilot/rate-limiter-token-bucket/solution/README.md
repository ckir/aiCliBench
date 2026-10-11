# Solution

```python
class TokenBucket:
    def __init__(self, rate: float, capacity: float) -> None:
        if rate <= 0 or capacity <= 0:
            raise ValueError("rate and capacity must be positive")
        self.rate = float(rate)
        self.capacity = float(capacity)
        self._tokens = float(capacity)
        self._last_time = time.time()

    def _refill(self, now: float) -> None:
        elapsed = max(0.0, now - self._last_time)
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_time = now

    def available_tokens(self, now: float | None = None) -> float:
        current_time = time.time() if now is None else now
        self._refill(current_time)
        return self._tokens

    def consume(self, tokens: float = 1.0, now: float | None = None) -> bool:
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        current_time = time.time() if now is None else now
        self._refill(current_time)
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False
```
