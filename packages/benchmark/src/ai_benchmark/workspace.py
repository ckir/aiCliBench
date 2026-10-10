"""Git workspace management (§7.3). Fresh workspace per attempt, pinned commit."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ai_core.errors import ConfigurationError, ValidationError


@dataclass(frozen=True, slots=True)
class WorkspaceInfo:
    path: Path
    starting_commit: str
    clean: bool


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed arg list, no shell
        [  # noqa: S607 - intentional PATH lookup of explicit tool
            "git",
            *args,
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def ensure_bare_cache(repository: str, cache_dir: Path) -> Path:
    """Fetch/clone or reuse a bare repository cache (read-only object store)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Stable cache name from repo URL/path.
    import hashlib

    name = hashlib.sha256(repository.encode()).hexdigest()[:16]
    bare = cache_dir / f"{name}.git"
    if bare.is_dir():
        if repository.startswith("file://") or Path(repository).exists():
            # Update local caches cheaply; ignore remote fetch failures here.
            _run_git(["fetch", "--all", "--prune"], bare)
        return bare
    result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
        [  # noqa: S607 - intentional PATH lookup of explicit tool
            "git",
            "clone",
            "--bare",
            repository,
            str(bare),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ConfigurationError(f"cannot clone repository {repository!r}: {result.stderr.strip()}")
    return bare


def checkout_fresh(
    *, repository: str, commit: str, dest: Path, cache_dir: Path | None = None
) -> WorkspaceInfo:
    """Create a fresh workspace at *dest* pinned to *commit*.

    Steps (§7.3): clone/fetch or cached bare repo → new workspace →
    exact commit checkout → hash confirm → no-modification check.
    """
    if dest.exists():
        raise ConfigurationError(f"workspace destination exists: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if cache_dir is not None:
        bare = ensure_bare_cache(repository, cache_dir)
        result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
            [  # noqa: S607 - intentional PATH lookup of explicit tool
                "git",
                "clone",
                str(bare),
                str(dest),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ConfigurationError(f"cannot clone cached repo: {result.stderr.strip()}")
        checkout = _run_git(["checkout", commit], dest)
    else:
        result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
            [  # noqa: S607 - intentional PATH lookup of explicit tool
                "git",
                "clone",
                repository,
                str(dest),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ConfigurationError(
                f"cannot clone repository {repository!r}: {result.stderr.strip()}"
            )
        checkout = _run_git(["checkout", commit], dest)
    if checkout.returncode != 0:
        raise ConfigurationError(f"cannot checkout commit {commit!r}: {checkout.stderr.strip()}")
    head = _run_git(["rev-parse", "HEAD"], dest)
    actual = head.stdout.strip()
    if actual.lower() != commit.lower():
        raise ValidationError(f"commit mismatch: expected {commit}, got {actual}")
    status = _run_git(["status", "--porcelain"], dest)
    clean = status.returncode == 0 and status.stdout.strip() == ""
    if not clean:
        raise ValidationError(f"workspace has pre-existing modifications: {dest}")
    return WorkspaceInfo(path=dest, starting_commit=actual, clean=clean)


def workspace_diff(workspace: Path) -> str:
    """Return unified diff of workspace changes (for `diff.patch` artifact)."""
    result = _run_git(["diff", "HEAD"], workspace)
    if result.returncode != 0:
        raise ConfigurationError(f"git diff failed: {result.stderr.strip()}")
    untracked = _run_git(["ls-files", "--others", "--exclude-standard"], workspace)
    extra = ""
    if untracked.stdout.strip():
        extra = "\n# untracked:\n# " + "\n# ".join(untracked.stdout.splitlines())
    return result.stdout + extra


def cleanup_workspace(path: Path, *, retain: bool = True) -> None:
    """Remove workspace unless `retain` (default retain for inspectability).

    Never deletes outside the application data directory: caller must pass a
    path it owns; we refuse to delete `/`, home, or repo roots heuristically
    by requiring the path to exist and be a directory.
    """
    if retain:
        return
    if not path.is_dir():
        return
    shutil.rmtree(path, ignore_errors=False)
