"""Exponential backoff calculation."""

import random


def compute_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay.

    Buggy: allows negative sleep values and exceeds max_delay.
    """
    if attempt < 0 or base_delay <= 0 or max_delay <= 0:
        raise ValueError("Invalid parameters")

    delay = base_delay * (2**attempt)
    if jitter:
        # BUG: adding random uniform centered at 0 can be negative or exceed max_delay!
        delay = delay + random.uniform(-base_delay, base_delay)
    return delay
