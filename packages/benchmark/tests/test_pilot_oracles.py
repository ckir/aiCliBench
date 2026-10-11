"""CI guard: every pilot task fails on its original commit and passes with its reference solution.

Run under ``uv run`` so ``python3`` resolves to the venv interpreter that has pytest.
"""

import os
from pathlib import Path

import pytest

from ai_benchmark.task_verify import verify_task

TASKS = Path(__file__).resolve().parents[3] / "tasks" / "pilot"
TASK_DIRS = sorted(p for p in TASKS.iterdir() if (p / "task.toml").is_file())


# The unmodified naive source takes ~5 min against the 1000x1000 hidden test; opt in explicitly.
SLOW = {"sparse-matrix-multiplication"}


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_pilot_task_oracle(task_dir: Path, tmp_path: Path):
    if task_dir.name in SLOW and not os.environ.get("CODEBENCH_VERIFY_SLOW"):
        pytest.skip("slow oracle; set CODEBENCH_VERIFY_SLOW=1 to run")
    result = verify_task(task_dir, work_dir=tmp_path)
    assert result.ok, result.errors
