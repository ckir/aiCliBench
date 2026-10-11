"""Sandbox Path Resolution Guard."""

import re
import urllib.parse
from pathlib import Path


class PathTraversalError(Exception):
    pass


def resolve_sandbox_path(sandbox_root: str | Path, untrusted_path: str) -> Path:
    if "\x00" in untrusted_path:
        raise PathTraversalError(f"Null byte in path: {untrusted_path!r}")

    # Decode (possibly multiply) percent-encoded sequences before inspection.
    decoded = untrusted_path
    for _ in range(5):
        step = urllib.parse.unquote(decoded)
        if step == decoded:
            break
        decoded = step
    if "\x00" in decoded:
        raise PathTraversalError(f"Null byte in path: {untrusted_path!r}")

    for candidate in (untrusted_path, decoded):
        if ".." in re.split(r"[\\/]+", candidate):
            raise PathTraversalError(f"Path outside sandbox: {untrusted_path}")

    root = Path(sandbox_root).resolve()
    resolved = (root / untrusted_path).resolve()
    if not resolved.is_relative_to(root):
        raise PathTraversalError(f"Path outside sandbox: {untrusted_path}")
    return resolved
