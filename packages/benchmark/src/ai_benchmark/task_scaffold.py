"""Task scaffolding (§7.1, §11.4). Create a new verifiable task from a template."""

from __future__ import annotations

from pathlib import Path

from ai_benchmark.task_materialize import materialize_repo, repin_task
from ai_benchmark.task_registry import validate_task
from ai_core.errors import ConfigurationError

RUN_TESTS_SH = """#!/bin/bash
# Trusted acceptance command. Runs hidden tests only; agent must not see these.
set -euo pipefail
EVAL_DIR="${EVALUATOR_DIR:-/evaluator}"
WORKSPACE_DIR="${WORKSPACE:-/workspace}"
cd "${WORKSPACE_DIR}" 2>/dev/null || true
export PYTHONPATH="${WORKSPACE_DIR}:${PYTHONPATH:-}"
# Prefer the mounted evaluator tests; fall back to EVALUATOR_DIR.
if [ -d "/evaluator/tests" ]; then
  python3 -m pytest /evaluator/tests -v
elif [ -d "${EVAL_DIR}/tests" ]; then
  python3 -m pytest "${EVAL_DIR}/tests" -v
else
  echo "evaluator tests not found" >&2
  exit 2
fi
"""

DOCKERFILE = """FROM python:3.12-slim
WORKDIR /workspace
COPY . .
RUN pip install --no-cache-dir pytest
"""

INSTRUCTION_MD = """Fix the `greet(name)` function in `app.py` so that it returns a proper greeting.

The function currently returns `\"Hello, \"` without the name.
It should return `\"Hello, {name}!\"`.

**Constraints:**
- Do not modify any tests, evaluator scripts, or task metadata.
- Only modify `app.py`.
- The function signature must remain `def greet(name: str) -> str:`.
"""

APP_PY = '''def greet(name: str) -> str:
    """Return a greeting for the given name."""
    return "Hello, "
'''

SOURCE_README = """# Task Source Code

This directory contains the buggy source code that needs to be fixed.

## Files

- `app.py` - Contains the buggy `greet()` function
- `test_visible.py` - Visible tests for local feedback (not used for grading)
"""

VISIBLE_TEST = '''"""Visible tests for local feedback only."""

from app import greet


def test_greet_starts_with_hello():
    assert greet("world").startswith("Hello, ")
'''

EVALUATOR_TEST = '''"""Hidden acceptance tests (never mounted into the agent workspace)."""

from app import greet  # ty: ignore[unresolved-import]


def test_greet_format():
    assert greet("Ada") == "Hello, Ada!"
'''

SOLUTION_README = """# Reference Solution

This directory contains the fixed version of the buggy code.

## Files

- `app.py` - The fixed `greet()` function
"""

SOLUTION_APP_PY = '''def greet(name: str) -> str:
    """Return a greeting for the given name."""
    return f"Hello, {name}!"
'''

TASK_TOML_TEMPLATE = """schema_version = 1
id = "{task_id}"
title = "{title}"
category = "{category}"
suite = "{suite}"
description = "{description}"
repository = "repo"
commit = "{commit}"
instruction_file = "instruction.md"
dockerfile = "environment/Dockerfile"
evaluator_command = ["bash", "/evaluator/run_tests.sh"]
timeout_seconds = 900
max_test_seconds = 300
cpu_limit = 2
memory_limit = "4g"
pids_limit = 256
network_enabled_for_agent = false
tags = ["python", "bugfix"]

[environment]
working_directory = "/workspace"
setup_command = []

[scoring]
acceptance_weight = 1.0
build_required = false
lint_required = false
typecheck_required = false
"""


def scaffold_task(
    tasks_root: Path,
    *,
    task_id: str,
    suite: str = "pilot",
    title: str,
    category: str,
    description: str = "",
) -> Path:
    """Create a new task directory with all required files and materialize its repo.

    Args:
        tasks_root: Root directory containing suite subdirectories.
        task_id: Unique identifier for the task.
        suite: Suite name (default: "pilot").
        title: Human-readable task title.
        category: Task category (e.g., "bugfix", "feature").
        description: Optional description.

    Returns:
        Path to the created task directory.

    Raises:
        ConfigurationError: If task directory already exists.
    """
    task_dir = tasks_root / suite / task_id
    if task_dir.exists():
        raise ConfigurationError(f"task already exists: {task_dir}")

    task_dir.mkdir(parents=True)
    (task_dir / "source").mkdir()
    (task_dir / "environment").mkdir()
    (task_dir / "evaluator" / "tests").mkdir(parents=True)
    (task_dir / "solution" / "files").mkdir(parents=True)

    # Write task.toml
    toml_content = TASK_TOML_TEMPLATE.format(
        task_id=task_id,
        title=title,
        category=category,
        suite=suite,
        description=description,
        commit="0" * 40,
    )
    (task_dir / "task.toml").write_text(toml_content, encoding="utf-8")

    # Write instruction.md
    (task_dir / "instruction.md").write_text(INSTRUCTION_MD, encoding="utf-8")

    # Write source files
    (task_dir / "source" / "app.py").write_text(APP_PY, encoding="utf-8")
    (task_dir / "source" / "README.md").write_text(SOURCE_README, encoding="utf-8")
    (task_dir / "source" / "test_visible.py").write_text(VISIBLE_TEST, encoding="utf-8")

    # Write evaluator files
    (task_dir / "evaluator" / "run_tests.sh").write_text(RUN_TESTS_SH, encoding="utf-8")
    (task_dir / "evaluator" / "run_tests.sh").chmod(0o755)
    (task_dir / "evaluator" / "tests" / "test_hidden.py").write_text(
        EVALUATOR_TEST, encoding="utf-8"
    )

    # Write environment
    (task_dir / "environment" / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")

    # Write solution files
    (task_dir / "solution" / "README.md").write_text(SOLUTION_README, encoding="utf-8")
    (task_dir / "solution" / "files" / "app.py").write_text(SOLUTION_APP_PY, encoding="utf-8")

    # Materialize the repo to generate a real commit
    result = materialize_repo(task_dir, check=False)
    if result.commit:
        # Update the pinned commit in task.toml
        repin_task(task_dir, result.commit)

    # Validate the task
    validation = validate_task(task_dir, check_repo=True)
    if not validation.ok:
        raise ConfigurationError(f"scaffolded task invalid: {validation.errors}")

    return task_dir
