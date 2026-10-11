"""Task repository materialization (§7.3). Deterministic repo generation from source/."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ai_core.errors import ConfigurationError

# Fixed git environment for deterministic commits
FIXED_GIT_ENV: dict[str, str] = {
    "GIT_AUTHOR_NAME": "CodeBench Demo",
    "GIT_AUTHOR_EMAIL": "demo@example.invalid",
    "GIT_COMMITTER_NAME": "CodeBench Demo",
    "GIT_COMMITTER_EMAIL": "demo@example.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
}


class MaterializeMismatchError(ConfigurationError):
    """Raised when generated commit doesn't match pinned commit."""

    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"commit mismatch: expected {expected}, got {actual}")


@dataclass(frozen=True, slots=True)
class MaterializeResult:
    task_id: str
    repo_path: Path | None
    commit: str | None
    pinned_commit: str
    action: Literal["kept", "generated", "skipped"]


def generated_commit_message(task_id: str) -> str:
    return f"initial: {task_id}"


def _is_task_relative_repo(repository: str) -> bool:
    return (
        not repository.startswith(("file://", "http://", "https://", "git@", "ssh://"))
        and not Path(repository).is_absolute()
    )


def _copy_source_to_temp(source_dir: Path, temp_dir: Path) -> None:
    """Copy all regular files from source/ to temp dir, skipping __pycache__ and .pyc."""
    for src_path in source_dir.rglob("*"):
        if not src_path.is_file():
            continue
        rel = src_path.relative_to(source_dir)
        if any(part in ("__pycache__", ".pytest_cache") for part in rel.parts):
            continue
        if rel.suffix == ".pyc":
            continue
        dst = temp_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst)


def _git_init_commit(repo_dir: Path, task_id: str) -> str:
    """Initialize git repo and commit, return the commit SHA."""
    env = {**os.environ, **FIXED_GIT_ENV}
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True, env=env)  # noqa: S607
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True, capture_output=True, env=env)  # noqa: S607
    msg = generated_commit_message(task_id)
    subprocess.run(  # noqa: S603 - fixed arg list, no shell
        ["git", "commit", "-q", "-m", msg],  # noqa: S607
        cwd=repo_dir,
        check=True,
        capture_output=True,
        env=env,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip().lower()


def _repo_is_clean(repo_dir: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],  # noqa: S607
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == ""


def _get_head_commit(repo_dir: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip().lower()


def materialize_repo(
    task_dir: Path, *, force: bool = False, check: bool = True
) -> MaterializeResult:
    """Materialize the task repository from source/.

    Args:
        task_dir: Path to task directory containing task.toml and source/
        force: If True, regenerate even if repo exists and matches
        check: If True, verify generated commit matches pinned commit

    Returns:
        MaterializeResult with action taken
    """
    from ai_benchmark.task_registry import load_task

    loaded = load_task(task_dir)
    task = loaded.definition
    task_id = task.id

    repo_path = task_dir / "repo"
    source_path = task_dir / "source"

    # If repository is not task-relative or source/ missing, skip
    if not _is_task_relative_repo(task.repository) or not source_path.is_dir():
        return MaterializeResult(
            task_id=task_id,
            repo_path=None,
            commit=None,
            pinned_commit=task.commit,
            action="skipped",
        )

    # If repo exists, check if it matches pinned commit and is clean
    if repo_path.is_dir() and (repo_path / ".git").is_dir():
        head = _get_head_commit(repo_path)
        if head == task.commit.lower() and _repo_is_clean(repo_path):
            return MaterializeResult(
                task_id=task_id,
                repo_path=repo_path,
                commit=head,
                pinned_commit=task.commit,
                action="kept",
            )
        if not force:
            if not _repo_is_clean(repo_path):
                raise ConfigurationError(f"task repo modified: {repo_path}; re-run with force")
            if head != task.commit.lower():
                raise MaterializeMismatchError(expected=task.commit, actual=head)
        # force=True or dirty: fall through to regenerate

    # Generate new repo in temp dir beside repo/
    temp_dir = repo_path.parent / f".repo-tmp-{task_id}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    try:
        _copy_source_to_temp(source_path, temp_dir)
        commit = _git_init_commit(temp_dir, task_id)

        if check and commit != task.commit.lower():
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise MaterializeMismatchError(expected=task.commit, actual=commit)

        # Atomically replace repo/
        if repo_path.exists():
            shutil.rmtree(repo_path)
        temp_dir.rename(repo_path)

        return MaterializeResult(
            task_id=task_id,
            repo_path=repo_path,
            commit=commit,
            pinned_commit=task.commit,
            action="generated",
        )
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def repin_task(task_dir: Path, commit: str) -> None:
    """Rewrite the commit line in task.toml."""
    task_toml = task_dir / "task.toml"
    lines = task_toml.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if line.strip().startswith("commit = "):
            new_lines.append(f'commit = "{commit}"')
        else:
            new_lines.append(line)
    task_toml.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
