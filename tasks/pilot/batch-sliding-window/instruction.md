# Optimize Sliding Window Statistics to O(1) Monotonic Queue

In `sliding_window.py`, `SlidingWindowStats` maintains statistical aggregates over the last $W$ elements of a stream of numbers.

The current implementation re-slices the list and calls `min()` and `max()` on every insertion, giving $O(W)$ per element ($O(N \times W)$ total).

### Requirements:
1. `SlidingWindowStats(window_size: int)`:
   - `window_size`: positive integer.
2. `push(val: float) -> None`:
   - Adds a new value to the sliding window. If more than `window_size` elements have been added, the oldest element is removed.
   - Must run in $O(1)$ amortized time using a monotonic deque (for min and max) and running sum (for mean).
3. `get_min() -> float`:
   - Returns the minimum value currently in the window in $O(1)$ time. Raises `ValueError` if window is empty.
4. `get_max() -> float`:
   - Returns the maximum value currently in the window in $O(1)$ time. Raises `ValueError` if window is empty.
5. `get_mean() -> float`:
   - Returns the arithmetic mean of current window elements in $O(1)$ time. Raises `ValueError` if window is empty.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
