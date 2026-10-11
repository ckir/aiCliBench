"""Sliding Window Statistics."""

from collections import deque


class SlidingWindowStats:
    def __init__(self, window_size: int) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        self.window_size = window_size
        self._buffer: deque[float] = deque()

    def push(self, val: float) -> None:
        # Slow naive implementation
        if len(self._buffer) >= self.window_size:
            self._buffer.popleft()
        self._buffer.append(val)

    def get_min(self) -> float:
        if not self._buffer:
            raise ValueError("empty window")
        return min(self._buffer)

    def get_max(self) -> float:
        if not self._buffer:
            raise ValueError("empty window")
        return max(self._buffer)

    def get_mean(self) -> float:
        if not self._buffer:
            raise ValueError("empty window")
        return sum(self._buffer) / len(self._buffer)
