"""SemVer 2.0 implementation."""

from __future__ import annotations

import re
from functools import total_ordering

SEMVER_REGEX = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


def _compare_identifier(a: str, b: str) -> int:
    a_num, b_num = a.isdigit(), b.isdigit()
    if a_num and b_num:
        return int(a) - int(b)
    if a_num and not b_num:
        return -1
    if not a_num and b_num:
        return 1
    return (a > b) - (a < b)


@total_ordering
class SemVer:
    def __init__(self, version_str: str) -> None:
        match = SEMVER_REGEX.match(version_str)
        if not match:
            raise ValueError(f"Invalid semver: {version_str}")
        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))
        self.prerelease = match.group(4) or None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.prerelease) == (
            other.major,
            other.minor,
            other.patch,
            other.prerelease,
        )

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Normal version has higher precedence than prerelease
        if self.prerelease is None or other.prerelease is None:
            return self.prerelease is not None and other.prerelease is None

        p1 = self.prerelease.split(".")
        p2 = other.prerelease.split(".")
        for a, b in zip(p1, p2):
            c = _compare_identifier(a, b)
            if c != 0:
                return c < 0
        return len(p1) < len(p2)
