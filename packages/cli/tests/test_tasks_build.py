"""Tests for `codebench tasks build` command (docker calls are patched out)."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ai_cli.codebench import app


def _make_task(root: Path, task_id: str = "example-task", suite: str = "pilot") -> Path:
    """Create a minimal task directory for testing."""
    task_dir = root / suite / task_id
    (task_dir / "environment").mkdir(parents=True, exist_ok=True)
    (task_dir / "evaluator").mkdir(parents=True, exist_ok=True)
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                f'id = "{task_id}"',
                'title = "Test Task"',
                'category = "bugfix"',
                f'suite = "{suite}"',
                'description = "test"',
                'repository = "https://example.invalid/r.git"',
                'commit = "0000000000000000000000000000000000000000"',
                'instruction_file = "instruction.md"',
                'dockerfile = "environment/Dockerfile"',
                'evaluator_command = ["bash", "/evaluator/run_tests.sh"]',
                "timeout_seconds = 900",
                "max_test_seconds = 300",
            ]
        ),
        encoding="utf-8",
    )
    (task_dir / "instruction.md").write_text("Fix the bug.", encoding="utf-8")
    (task_dir / "environment" / "Dockerfile").write_text(
        "FROM python:3.12-slim\n", encoding="utf-8"
    )
    (task_dir / "evaluator" / "run_tests.sh").write_text(
        "#!/bin/bash\necho 'passed: 1'\nexit 0\n", encoding="utf-8"
    )
    (task_dir / "evaluator" / "run_tests.sh").chmod(0o755)
    return task_dir


def test_tasks_build_help():
    runner = CliRunner()
    result = runner.invoke(app, ["tasks", "build", "--help"])
    assert result.exit_code == 0
    assert "build" in result.output.lower()
    assert "--suite" in result.output
    assert "--all" in result.output


def test_tasks_build_requires_suite_or_all():
    runner = CliRunner()
    result = runner.invoke(app, ["tasks", "build"])
    assert result.exit_code == 2


def test_tasks_build_suite_invokes_docker_build(tmp_path: Path):
    """Build invokes `build_image` once per task in the suite with the task tag."""
    import ai_cli.codebench as mod

    calls: list[dict] = []

    def fake_build(**kwargs):
        calls.append(kwargs)
        return kwargs["tag"]

    tasks_root = tmp_path / "tasks"
    _make_task(tasks_root, "example-task", "pilot")
    with patch.dict(mod.__dict__, docker_available=lambda: True, build_image=fake_build):
        result = CliRunner().invoke(
            app, ["tasks", "build", "--suite", "pilot"], env={"TASKS_ROOT": str(tasks_root)}
        )
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls[0]["tag"] == "codebench-task:example-task"
    assert "BUILT" in result.output


def test_tasks_build_all_flag(tmp_path: Path):
    """`--all` builds across every suite directory under the tasks root."""
    import ai_cli.codebench as mod

    built: list[str] = []
    tasks_root = tmp_path / "tasks"
    _make_task(tasks_root, "example-task", "pilot")
    _make_task(tasks_root, "task2", "other-suite")
    with patch.dict(
        mod.__dict__,
        docker_available=lambda: True,
        build_image=lambda **kw: built.append(kw["tag"]) or kw["tag"],
    ):
        result = CliRunner().invoke(
            app, ["tasks", "build", "--all"], env={"TASKS_ROOT": str(tasks_root)}
        )
    assert result.exit_code == 0, result.output
    assert sorted(built) == ["codebench-task:example-task", "codebench-task:task2"]


def test_tasks_build_skips_missing_dockerfile(tmp_path: Path):
    """A task whose Dockerfile is absent is skipped, not built."""
    import ai_cli.codebench as mod

    tasks_root = tmp_path / "tasks"
    task_dir = _make_task(tasks_root, "no-dockerfile", "pilot")
    (task_dir / "environment" / "Dockerfile").unlink()

    def fail_build(**kwargs):
        raise AssertionError("build_image must not be called")

    with patch.dict(mod.__dict__, docker_available=lambda: True, build_image=fail_build):
        result = CliRunner().invoke(
            app, ["tasks", "build", "--suite", "pilot"], env={"TASKS_ROOT": str(tasks_root)}
        )
    # load_task rejects the task before build (missing Dockerfile is a load error).
    assert result.exit_code == 0
    assert "Cannot load suite" in result.output or "SKIP" in result.output


def test_tasks_build_without_docker_exits_dependency(tmp_path: Path):
    import ai_cli.codebench as mod

    with patch.dict(mod.__dict__, docker_available=lambda: False):
        result = CliRunner().invoke(app, ["tasks", "build", "--suite", "pilot"])
    assert result.exit_code == 4
