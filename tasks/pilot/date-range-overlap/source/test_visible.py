from datetime import datetime

from date_range import DateRange


def test_clear_overlap():
    d1 = DateRange(datetime(2026, 1, 1, 10), datetime(2026, 1, 1, 12))
    d2 = DateRange(datetime(2026, 1, 1, 11), datetime(2026, 1, 1, 13))
    assert d1.overlaps(d2)
