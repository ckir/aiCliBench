"""Hidden acceptance tests for Levenshtein."""

import time

from levenshtein import levenshtein_distance  # ty: ignore[unresolved-import]


def test_large_strings_performance():
    s1 = "abcdefghij" * 50  # 500 chars
    s2 = "abcdefghij" * 49 + "1234567890"

    start = time.perf_counter()
    dist = levenshtein_distance(s1, s2)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.2, f"Too slow: {elapsed:.3f}s"
    assert dist == 10


def test_empty_and_identical():
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("hello", "") == 5
    assert levenshtein_distance("exact", "exact") == 0
