"""Hidden acceptance tests for Path Guard."""

from pathlib import Path

import pytest
from path_guard import PathTraversalError, resolve_sandbox_path  # ty: ignore[unresolved-import]


def test_rejects_parent_traversal(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    with pytest.raises(PathTraversalError):
        resolve_sandbox_path(sandbox, "../outside.txt")

    with pytest.raises(PathTraversalError):
        resolve_sandbox_path(sandbox, "sub/../../secret.txt")

    with pytest.raises(PathTraversalError):
        resolve_sandbox_path(sandbox, "/etc/passwd")


def test_rejects_null_byte(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    with pytest.raises(PathTraversalError):
        resolve_sandbox_path(sandbox, "valid.txt\x00.evil")


def test_allows_valid_child_path(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    child = sandbox / "docs" / "readme.txt"
    child.parent.mkdir()
    child.touch()

    resolved = resolve_sandbox_path(sandbox, "docs/readme.txt")
    assert resolved == child.resolve()
