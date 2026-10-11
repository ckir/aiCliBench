"""Stable ID helpers."""

from __future__ import annotations

import re
import uuid

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def new_id(prefix: str = "") -> str:
    """Return a unique, URL/hostname-safe identifier.

    Args:
        prefix: Optional human-readable prefix (e.g. ``"req"``, ``"run"``).

    Returns:
        A unique identifier string. If prefix is provided, the format is
        ``prefix_suffix`` where suffix is a 12-character hex string.
        If no prefix, returns only the 12-character hex string.
    """
    suffix = uuid.uuid4().hex[:12]
    if not prefix:
        return suffix
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "-", prefix).strip("-_") or "id"
    return f"{cleaned}_{suffix}"


def is_valid_id(value: str) -> bool:
    """Return ``True`` when ``value`` looks like an ID produced by :func:`new_id`.

    Validates both the simple form (12-char hex) and the prefixed form
    ``prefix_suffix`` where prefix is alphanumeric with hyphens/underscores
    and suffix is a 12-char hex string.

    Args:
        value: The string to validate.

    Returns:
        ``True`` if the value matches the expected ID format, ``False`` otherwise.
    """
    if not value:
        return False
    # Allow prefixed form ``prefix_suffix``.
    candidates = [value] if _ID_PATTERN.match(value) else []
    if candidates:
        return True
    if "_" in value:
        prefix, _, suffix = value.rpartition("_")
        return bool(prefix) and bool(suffix) and _ID_PATTERN.match(value) is not None
    return False
