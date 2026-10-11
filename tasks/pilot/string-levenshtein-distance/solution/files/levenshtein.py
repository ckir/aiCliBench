"""Levenshtein distance calculation."""


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance with two-row Wagner-Fischer, O(min(m, n)) space."""
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)
    previous = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1, start=1):
        current = [i]
        for j, c2 in enumerate(s2, start=1):
            current.append(
                min(
                    previous[j] + 1,  # deletion
                    current[j - 1] + 1,  # insertion
                    previous[j - 1] + (c1 != c2),  # substitution
                )
            )
        previous = current
    return previous[-1]
