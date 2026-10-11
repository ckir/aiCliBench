"""Sliding Window Statistics."""

from collections import deque


class SlidingWindowStats:
    def __init__(self, window_size: int) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        self.window_size = window_size
        self._buffer: deque[float] = deque()
        # Monotonic deques of (index, value): min strictly increasing, max strictly decreasing.
        self._min_q: deque[tuple[int, float]] = deque()
        self._max_q: deque[tuple[int, float]] = deque()
        self._sum = 0.0
        self._count = 0

    def push(self, val: float) -> None:
        idx = self._count
        self._count += 1
        if len(self._buffer) >= self.window_size:
            self._sum -= self._buffer.popleft()
        self._buffer.append(val)
        self._sum += val

        while self._min_q and self._min_q[-1][1] >= val:
            self._min_q.pop()
        self._min_q.append((idx, val))
        while self._max_q and self._max_q[-1][1] <= val:
            self._max_q.pop()
        self._max_q.append((idx, val))

        oldest = idx - self.window_size + 1
        while self._min_q[0][0] < oldest:
            self._min_q.popleft()
        while self._max_q[0][0] < oldest:
            self._max_q.popleft()

    def get_min(self) -> float:
        if not self._buffer:
            raise ValueError("empty window")
        return self._min_q[0][1]

    def get_max(self) -> float:
        if not self._buffer:
            raise ValueError("empty window")
        return self._max_q[0][1]

    def get_mean(self) -> float:
        if not self._buffer:
            raise ValueError("empty window")
        return self._sum / len(self._buffer)
