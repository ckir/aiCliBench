# Refactor Service Caller with Circuit Breaker Pattern

In `circuit_breaker.py`, implement the `CircuitBreaker` pattern to guard calls against cascading failures.

### States:
- `CLOSED`: Normal operation. Invocations pass through to the target function. If consecutive failures reach `failure_threshold`, transition to `OPEN`.
- `OPEN`: Failures exceeded threshold. Invocations fail immediately by raising `CircuitBreakerOpenException` without invoking the target function. After `recovery_timeout` seconds, transition to `HALF_OPEN`.
- `HALF_OPEN`: Trial state. Exactly one trial invocation is attempted. If it succeeds, reset failures to 0 and transition back to `CLOSED`. If it fails, transition immediately back to `OPEN` and reset the recovery timer.

### Requirements:
1. `class CircuitBreakerOpenException(Exception)`
2. `CircuitBreaker(failure_threshold: int = 3, recovery_timeout: float = 10.0)`
3. `call(func: Callable, *args, **kwargs) -> Any`:
   - Executes `func(*args, **kwargs)` subject to circuit state.
   - Accepts custom `now: float | None = None` kwarg or uses `time.time()`.
4. Properties: `state` (returns `"CLOSED"`, `"OPEN"`, `"HALF_OPEN"`), `failure_count` (int).

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
