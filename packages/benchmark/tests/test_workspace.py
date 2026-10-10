import subprocess
from pathlib import Path

import pytest

from ai_benchmark.workspace import checkout_fresh, ensure_bare_cache, workspace_diff
from ai_core.errors import ConfigurationError


def _make_repo(root: Path) -> tuple[str, str]:
    repo = root / "origin"
    repo.mkdir()
    subprocess.run(
        ["git", "init"],  # noqa: S607 - intentional PATH lookup of explicit tool
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [  # noqa: S607 - intentional PATH lookup of explicit tool
            "git",
            "config",
            "user.email",
            "test@example.invalid",
        ],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        [  # noqa: S607 - intentional PATH lookup of explicit tool
            "git",
            "config",
            "user.name",
            "Test",
        ],
        cwd=repo,
        check=True,
    )
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "."],  # noqa: S607 - intentional PATH lookup of explicit tool
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],  # noqa: S607 - intentional PATH lookup of explicit tool
        cwd=repo,
        check=True,
        capture_output=True,
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607 - intentional PATH lookup of explicit tool
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return str(repo), commit


def test_checkout_fresh_pinned_and_clean(tmp_path: Path):
    repo, commit = _make_repo(tmp_path)
    dest = tmp_path / "ws" / "attempt-1"
    info = checkout_fresh(repository=repo, commit=commit, dest=dest, cache_dir=tmp_path / "cache")
    assert info.starting_commit == commit
    assert info.clean is True
    # Second attempt gets its own fresh workspace.
    dest2 = tmp_path / "ws" / "attempt-2"
    info2 = checkout_fresh(repository=repo, commit=commit, dest=dest2, cache_dir=tmp_path / "cache")
    assert info2.starting_commit == commit
    (dest2 / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    diff = workspace_diff(dest2)
    assert "VALUE" in diff
    # First workspace untouched.
    assert workspace_diff(dest).strip() == "" or "untracked" in workspace_diff(dest)


def test_checkout_refuses_existing_dest(tmp_path: Path):
    repo, commit = _make_repo(tmp_path)
    dest = tmp_path / "ws"
    dest.mkdir()
    with pytest.raises(ConfigurationError):
        checkout_fresh(repository=repo, commit=commit, dest=dest)


def test_bare_cache_reused(tmp_path: Path):
    repo, _ = _make_repo(tmp_path)
    first = ensure_bare_cache(repo, tmp_path / "cache")
    second = ensure_bare_cache(repo, tmp_path / "cache")
    assert first == second
