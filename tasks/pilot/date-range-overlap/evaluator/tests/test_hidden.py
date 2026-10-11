"""Hidden acceptance tests for DateRange."""

from datetime import datetime

from date_range import DateRange  # ty: ignore[unresolved-import]


def test_adjacent_ranges_do_not_overlap():
    d1 = DateRange(datetime(2026, 1, 1, 10), datetime(2026, 1, 1, 11))
    d2 = DateRange(datetime(2026, 1, 1, 11), datetime(2026, 1, 1, 12))
    assert not d1.overlaps(d2)
    assert not d2.overlaps(d1)
    assert d1.intersection(d2) is None


def test_contains_half_open():
    d = DateRange(datetime(2026, 1, 1, 10), datetime(2026, 1, 1, 11))
    assert d.contains(datetime(2026, 1, 1, 10))
    assert d.contains(datetime(2026, 1, 1, 10, 30))
    assert not d.contains(datetime(2026, 1, 1, 11))


def test_exact_intersection():
    d1 = DateRange(datetime(2026, 1, 1, 10), datetime(2026, 1, 1, 14))
    d2 = DateRange(datetime(2026, 1, 1, 12), datetime(2026, 1, 1, 16))
    inter = d1.intersection(d2)
    assert inter is not None
    assert inter.start == datetime(2026, 1, 1, 12)
    assert inter.end == datetime(2026, 1, 1, 14)
