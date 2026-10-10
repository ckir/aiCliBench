"""Task-relative path safety (§7.1). Rejects traversal and symlink escapes."""

from __future__ import annotations

from pathlib import Path

from ai_core.errors import ValidationError


def safe_join(base: Path, rel: str) -> Path:
    """Join *rel* onto *base* and ensure the result stays inside *base*.

    Raises:
        ValidationError: on absolute paths, ``..`` escapes, or symlink escapes.
    """
    if not rel:
        raise ValidationError("empty relative path", field="path")
    candidate = Path(rel)
    if candidate.is_absolute():
        raise ValidationError(f"absolute path not allowed: {rel!r}", field="path")
    if ".." in candidate.parts:
        raise ValidationError(f"path escapes task directory: {rel!r}", field="path")
    resolved_base = base.resolve()
    # Resolve without requiring existence for pure validation; then check prefix.
    joined = resolved_base / candidate
    # `resolve(strict=False)` normalizes `..` and symlinks for existing parts.
    resolved = joined.resolve(strict=False)
    try:
        resolved.relative_to(resolved_base)
    except ValueError as exc:
        raise ValidationError(f"path escapes task directory: {rel!r}", field="path") from exc
    return resolved


def ensure_within(base: Path, candidate: Path) -> Path:
    """Ensure an already-joined *candidate* stays within *base* (symlink-aware)."""
    resolved_base = base.resolve()
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(resolved_base)
    except ValueError as exc:
        raise ValidationError(f"path escapes base directory: {candidate!r}", field="path") from exc
    return resolved
