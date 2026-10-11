"""Exponential backoff calculation."""

import random


def compute_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay (full jitter)."""
    if attempt < 0 or base_delay <= 0 or max_delay <= 0:
        raise ValueError("Invalid parameters")
    temp = min(max_delay, base_delay * (2**attempt))
    if jitter:
        return random.uniform(0.0, temp)
    return temp
