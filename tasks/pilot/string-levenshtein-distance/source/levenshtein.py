"""Levenshtein distance calculation."""


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance.

    Naive exponential recursion (crashes / times out).
    """
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)
    if s1[0] == s2[0]:
        return levenshtein_distance(s1[1:], s2[1:])
    return (
        1
        + min(
            levenshtein_distance(s1[1:], s2),  # deletion
            levenshtein_distance(s1, s2[1:]),  # insertion
            levenshtein_distance(s1[1:], s2[1:]),  # substitution
        )
    )
