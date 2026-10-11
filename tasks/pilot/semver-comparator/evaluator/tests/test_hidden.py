"""Hidden acceptance tests for SemVer 2.0 comparator."""

from semver import SemVer  # ty: ignore[unresolved-import]


def test_numeric_prerelease_comparison():
    v2 = SemVer("1.0.0-alpha.2")
    v10 = SemVer("1.0.0-alpha.10")
    assert v2 < v10
    assert not (v10 < v2)


def test_numeric_vs_alpha_precedence():
    # Numeric identifier always has lower precedence than non-numeric identifier
    num = SemVer("1.0.0-alpha.1")
    alpha = SemVer("1.0.0-alpha.beta")
    assert num < alpha


def test_prerelease_length_precedence():
    assert SemVer("1.0.0-alpha") < SemVer("1.0.0-alpha.1")
    assert SemVer("1.0.0-alpha.1") < SemVer("1.0.0-alpha.1.beta")
