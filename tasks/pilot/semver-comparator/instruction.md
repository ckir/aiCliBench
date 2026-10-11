# Fix SemVer 2.0 Pre-release Comparison

In `semver.py`, the `SemVer` class represents a semantic version (`major.minor.patch[-prerelease]`).

Per SemVer 2.0 specification §11:
- A normal version has greater precedence than a pre-release version with the same major.minor.patch (e.g. `1.0.0 > 1.0.0-alpha`).
- When comparing pre-release components (dot-separated):
  - Identifiers consisting of only digits are compared numerically (e.g. `1.0.0-alpha.2 < 1.0.0-alpha.10`).
  - Identifiers with letters/hyphens are compared lexicographically in ASCII sort order.
  - A numeric identifier always has lower precedence than a non-numeric identifier.
  - A larger set of pre-release fields has a higher precedence than a smaller set, if all of the preceding identifiers are equal.

Currently, the implementation in `semver.py` compares all pre-release identifiers lexicographically as strings, which causes `"10" < "2"` to evaluate as true, breaking version comparisons.

Fix `semver.py` so comparison (`<`, `<=`, `>`, `>=`, `==`) conforms to SemVer 2.0.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
