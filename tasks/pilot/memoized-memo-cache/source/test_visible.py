from memo_cache import memoize


@memoize(maxsize=10)
def identity(x):
    return x


def test_decorated_call():
    assert identity(5) == 5
