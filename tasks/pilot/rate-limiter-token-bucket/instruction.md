# Implement Token Bucket Rate Limiter

In `token_bucket.py`, implement the `TokenBucket` class for rate limiting.

### Requirements:
1. `__init__(rate: float, capacity: float)`:
   - `rate`: number of tokens added per second (must be > 0).
   - `capacity`: maximum token burst capacity (must be > 0).
   - Initially, the bucket starts completely full (`tokens == capacity`).
2. `consume(tokens: float = 1.0, now: float | None = None) -> bool`:
   - Checks if at least `tokens` are available at timestamp `now` (defaulting to current wall clock `time.time()`).
   - If available, deducts `tokens` from the bucket and returns `True`.
   - If insufficient, does not deduct any tokens and returns `False`.
   - Raises `ValueError` if `tokens <= 0`.
3. `available_tokens(now: float | None = None) -> float`:
   - Computes tokens available at timestamp `now` without consuming them. Cannot exceed `capacity`.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
