# Optimize Levenshtein Distance to O(min(M, N)) Space

In `levenshtein.py`, `levenshtein_distance(s1: str, s2: str) -> int` calculates the minimum number of single-character edits (insertions, deletions, substitutions) required to transform `s1` into `s2`.

The current naive implementation uses unmemoized recursion, which suffers from $O(3^N)$ exponential time complexity and hits Python's recursion limit on strings longer than 15 characters.

### Requirements:
1. Implement iterative Dynamic Programming with $O(\min(|s1|, |s2|))$ auxiliary memory (using only two rows or single array swap).
2. Computes correct Levenshtein distance for strings of any length up to 10,000 characters.
3. Edge cases:
   - Either or both strings empty: `levenshtein_distance("", "abc") == 3`.
   - Identical strings: distance is 0.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
