"""CLI tests: `codebench --help` and task commands (no providers, no docker)."""

from pathlib import Path

from typer.testing import CliRunner

from ai_cli.codebench import app


def test_codebench_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.output
    assert "tasks" in result.output


def test_tasks_list_and_validate():
    runner = CliRunner()
    listed = runner.invoke(app, ["tasks", "list"])
    assert listed.exit_code == 0
    assert "example-task" in listed.output

    validated = runner.invoke(app, ["tasks", "validate", "example-task"])
    assert validated.exit_code == 0
    assert "VALID" in validated.output


def test_runs_list_empty_ok(tmp_path: Path, monkeypatch):
    import tempfile

    runner = CliRunner()
    with tempfile.TemporaryDirectory() as td:
        config = Path(td) / "benchmark.toml"
        config.write_text(
            '[data]\ndirectory = "runs"\ndatabase = "runs/codebench.sqlite3"\n'
            "[execution]\n[agents.claude]\n[agents.antigravity]\n[report]\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(td)
        result = runner.invoke(app, ["runs", "list"])
        assert result.exit_code == 0
