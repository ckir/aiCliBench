from sliding_window import SlidingWindowStats


def test_basic_window():
    sw = SlidingWindowStats(3)
    sw.push(10)
    sw.push(20)
    sw.push(30)
    assert sw.get_min() == 10
    assert sw.get_max() == 30
    assert sw.get_mean() == 20
