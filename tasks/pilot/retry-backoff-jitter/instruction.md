# Fix Exponential Backoff Full Jitter Delay Calculation

In `retry.py`, `compute_backoff(attempt, base_delay=1.0, max_delay=60.0)` calculates the delay before the next retry attempt using full jitter.

The full jitter algorithm (per AWS Architecture guidelines) calculates:
$$temp = \min(max\_delay, base\_delay \times 2^{attempt})$$
$$sleep = \text{uniform}(0, temp)$$

Currently, the implementation in `retry.py` adds a random uniform offset centered at zero, which frequently yields negative sleep values (causing crashes in `time.sleep`) or exceeds `max_delay`.

Fix `compute_backoff` in `retry.py` so that:
1. Attempt 0 uses base exponential factor $2^0 = 1$.
2. Calculated delay is always non-negative: $0.0 \le delay \le \min(max\_delay, base\_delay \times 2^{attempt})$.
3. When `jitter=False`, deterministic exponential backoff $\min(max\_delay, base\_delay \times 2^{attempt})$ is returned.
4. Input validation rejects negative `attempt`, `base_delay <= 0`, or `max_delay <= 0`.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
