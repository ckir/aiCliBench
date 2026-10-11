"""Tests for task_materialize module."""

import shutil
import tempfile
from pathlib import Path

import pytest

from ai_benchmark.task_materialize import (
    MaterializeMismatchError,
    materialize_repo,
    repin_task,
)
from ai_core.errors import ConfigurationError


def _write_source_task(tmp_path: Path, task_id: str, pinned: str = "0" * 40) -> Path:
    """Create a minimal task directory with source/ and task.toml."""
    task_dir = tmp_path / "pilot" / task_id
    task_dir.mkdir(parents=True)
    (task_dir / "source").mkdir()
    (task_dir / "source" / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (task_dir / "source" / "README.md").write_text("# Task\n", encoding="utf-8")
    (task_dir / "source" / "test_visible.py").write_text("def test():\n    pass\n", encoding="utf-8")
    (task_dir / "evaluator").mkdir()
    (task_dir / "evaluator" / "run_tests.sh").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    (task_dir / "evaluator" / "run_tests.sh").chmod(0o755)
    (task_dir / "environment").mkdir()
    (task_dir / "environment" / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (task_dir / "task.toml").write_text(
        f"""schema_version = 1
id = "{task_id}"
title = "Test"
category = "bugfix"
suite = "pilot"
description = "test"
repository = "repo"
commit = "{pinned}"
instruction_file = "instruction.md"
dockerfile = "environment/Dockerfile"
evaluator_command = ["bash", "/evaluator/run_tests.sh"]
timeout_seconds = 900
max_test_seconds = 300
""",
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text("Fix the bug.", encoding="utf-8")
    return task_dir


def test_materialize_generates_and_repins(tmp_path: Path):
    task = _write_source_task(tmp_path, "t1")
    first = materialize_repo(task, check=False)
    assert first.action == "generated"
    assert first.commit is not None
    assert len(first.commit) == 40

    repin_task(task, first.commit)
    assert materialize_repo(task).action == "kept"

    shutil.rmtree(task / "repo")
    again = materialize_repo(task)
    assert again.action == "generated"
    assert again.commit == first.commit  # deterministic


def test_materialize_mismatch_raises(tmp_path: Path):
    task = _write_source_task(tmp_path, "t2", pinned="0" * 40)
    with pytest.raises(MaterializeMismatchError) as exc_info:
        materialize_repo(task, check=True)
    assert exc_info.value.expected == "0" * 40
    assert exc_info.value.actual is not None


def test_materialize_dirty_repo_rejected(tmp_path: Path):
    task = _write_source_task(tmp_path, "t3")
    # First generate and repin
    first = materialize_repo(task, check=False)
    repin_task(task, first.commit)
    assert materialize_repo(task).action == "kept"

    # Make repo dirty
    (task / "repo" / "extra.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="task repo modified"):
        materialize_repo(task, force=False)

    # With force, should regenerate
    result = materialize_repo(task, force=True)
    assert result.action == "generated"


def test_materialize_skips_remote_repository(tmp_path: Path):
    task = _write_source_task(tmp_path, "t4")
    # Change repository to remote
    task_toml = task / "task.toml"
    content = task_toml.read_text(encoding="utf-8")
    content = content.replace('repository = "repo"', 'repository = "https://example.invalid/r.git"')
    task_toml.write_text(content, encoding="utf-8")

    result = materialize_repo(task)
    assert result.action == "skipped"
    assert result.repo_path is None


def test_repin_rewrites_only_commit_line(tmp_path: Path):
    task = _write_source_task(tmp_path, "t5")
    original = (task / "task.toml").read_bytes()
    first = materialize_repo(task, check=False)
    repin_task(task, first.commit)
    new_content = (task / "task.toml").read_bytes()
    # Only the commit line should change
    orig_lines = original.splitlines()
    new_lines = new_content.splitlines()
    assert len(orig_lines) == len(new_lines)
    diffs = [(o, n) for o, n in zip(orig_lines, new_lines) if o != n]
    assert len(diffs) == 1
    assert b'commit = "' in diffs[0][0]
    assert b'commit = "' in diffs[0][1]