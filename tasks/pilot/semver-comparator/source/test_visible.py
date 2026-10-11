from semver import SemVer


def test_standard_versions():
    assert SemVer("1.0.0") < SemVer("2.0.0")
    assert SemVer("1.2.0") < SemVer("1.2.1")
    assert SemVer("1.0.0-alpha") < SemVer("1.0.0")
