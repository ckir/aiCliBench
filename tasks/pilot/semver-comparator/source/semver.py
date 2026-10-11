"""SemVer 2.0 implementation."""

from __future__ import annotations

import re
from functools import total_ordering

SEMVER_REGEX = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


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

    def _cmp_key(self) -> tuple:
        # BUG: compares prerelease split by dot strictly as strings
        pre_parts = self.prerelease.split(".") if self.prerelease else []
        # In current buggy code, prerelease presence has flawed precedence
        return (self.major, self.minor, self.patch, pre_parts)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.prerelease) == (
            other.major,
            other.minor,
            other.patch,
            other.prerelease,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Normal version has higher precedence than prerelease
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        if self.prerelease is None and other.prerelease is None:
            return False

        # Both have prerelease: compare identifier by identifier
        p1 = self.prerelease.split(".")  # ty: ignore[unresolved-attribute]
        p2 = other.prerelease.split(".")  # ty: ignore[unresolved-attribute]
        for a, b in zip(p1, p2):
            if a != b:
                # BUG: String comparison treats "10" < "2"
                return a < b
        return len(p1) < len(p2)
