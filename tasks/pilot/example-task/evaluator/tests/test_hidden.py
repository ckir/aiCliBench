"""Hidden acceptance tests (never mounted into the agent workspace)."""

from calc import add  # ty: ignore[unresolved-import]


def test_add_positive():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, 1) == 0


def test_add_zero():
    assert add(0, 0) == 0
