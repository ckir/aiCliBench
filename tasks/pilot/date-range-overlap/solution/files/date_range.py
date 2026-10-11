"""Date range interval operations."""

from __future__ import annotations

from datetime import datetime


class DateRange:
    def __init__(self, start: datetime, end: datetime) -> None:
        if start >= end:
            raise ValueError(f"start ({start}) must be before end ({end})")
        self.start = start
        self.end = end

    def contains(self, dt: datetime) -> bool:
        return self.start <= dt < self.end

    def overlaps(self, other: DateRange) -> bool:
        return self.start < other.end and other.start < self.end

    def intersection(self, other: DateRange) -> DateRange | None:
        if not self.overlaps(other):
            return None
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        if start >= end:
            return None
        return DateRange(start, end)
