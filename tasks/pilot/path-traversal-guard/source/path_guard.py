"""Sandbox Path Resolution Guard."""

from pathlib import Path


class PathTraversalError(Exception):
    pass


def resolve_sandbox_path(sandbox_root: str | Path, untrusted_path: str) -> Path:
    # Stub: insecure direct join
    return Path(sandbox_root) / untrusted_path
