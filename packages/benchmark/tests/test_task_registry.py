from pathlib import Path

import pytest

from ai_benchmark.task_registry import discover_tasks, load_task, validate_task
from ai_core.errors import ConfigurationError


def _write_task(
    root: Path,
    *,
    task_id: str = "example-task",
    suite: str = "pilot",
    commit: str = "0" * 40,
    instruction: str = "Fix the bug.",
    instruction_file: str = "instruction.md",
    dockerfile: str = "environment/Dockerfile",
) -> Path:
    task_dir = root / suite / task_id
    (task_dir / "environment").mkdir(parents=True, exist_ok=True)
    (task_dir / "evaluator").mkdir(parents=True, exist_ok=True)
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                f'id = "{task_id}"',
                'title = "Example"',
                'category = "bugfix"',
                f'suite = "{suite}"',
                'description = "desc"',
                'repository = "https://example.invalid/r.git"',
                f'commit = "{commit}"',
                f'instruction_file = "{instruction_file}"',
                f'dockerfile = "{dockerfile}"',
                'evaluator_command = ["bash", "/evaluator/run_tests.sh"]',
                "timeout_seconds = 900",
                "max_test_seconds = 300",
            ]
        ),
        encoding="utf-8",
    )
    (task_dir / instruction_file).write_text(instruction, encoding="utf-8")
    (task_dir / dockerfile).write_text("FROM python:3.12-slim\n", encoding="utf-8")
    return task_dir


def test_load_task_and_wrapper_identity(tmp_path: Path):
    task_dir = _write_task(tmp_path, instruction="Fix the parser edge case.")
    loaded = load_task(task_dir)
    assert loaded.definition.id == "example-task"
    assert loaded.instruction_sha256
    # Same bytes → same wrapper for both agents.
    second = load_task(task_dir)
    assert loaded.wrapped_prompt == second.wrapped_prompt
    assert loaded.wrapped_sha256 == second.wrapped_sha256
    assert loaded.prompt_wrapper_version.startswith("codebench-")


def test_task_rejects_bad_commit(tmp_path: Path):
    task_dir = _write_task(tmp_path, commit="main")
    with pytest.raises(ConfigurationError):
        load_task(task_dir)


def test_task_rejects_traversal(tmp_path: Path):
    task_dir = _write_task(tmp_path, instruction_file="../evil.md")
    with pytest.raises(ConfigurationError, match="invalid"):
        load_task(task_dir)


def test_discover_and_suite_mismatch(tmp_path: Path):
    _write_task(tmp_path, task_id="a", suite="pilot")
    _write_task(tmp_path, task_id="b", suite="pilot")
    tasks = discover_tasks(tmp_path / "pilot" and tmp_path, suite="pilot")
    assert len(tasks) == 2
    # Suite mismatch: directory pilot but metadata says other.
    bad = _write_task(tmp_path, task_id="c", suite="other")
    # Move it under pilot to trigger mismatch.
    import shutil

    dest = tmp_path / "pilot" / "c"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(bad), str(dest))
    with pytest.raises(ConfigurationError):
        discover_tasks(tmp_path, suite="pilot")


def test_validate_task_no_agent(tmp_path: Path):
    task_dir = _write_task(tmp_path)
    result = validate_task(task_dir, check_repo=False)
    assert result.ok is True
    assert result.task_id == "example-task"
