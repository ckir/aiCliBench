# Fix Half-Open Interval Overlap in DateRange

In `date_range.py`, the `DateRange` class models a half-open time interval `[start, end)` where `start` is inclusive and `end` is exclusive (`start < end`).

Currently, `overlaps(other)` uses `<=` instead of strict `<` on the boundaries, meaning adjacent intervals like `[10:00, 11:00)` and `[11:00, 12:00)` are incorrectly reported as overlapping.

Fix `date_range.py` so that:
1. `overlaps(other)` returns `True` if and only if two half-open intervals share a non-zero time intersection (`max(self.start, other.start) < min(self.end, other.end)`). Adjacent intervals must NOT overlap.
2. `intersection(other)` returns a new `DateRange` representing the overlapping sub-interval if they overlap, or `None` if they do not.
3. `contains(timestamp)` returns `True` if `start <= timestamp < end`.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
