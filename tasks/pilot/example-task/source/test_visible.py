"""Visible tests: must pass before and after the fix (import sanity)."""

from calc import add


def test_importable():
    assert callable(add)
