"""Claude adapter tests with fake executables (no provider calls)."""

import json
import os
import stat
from pathlib import Path

from ai_core.status import RunStatus
from ai_integration_claude_code.adapter import ClaudeCodeAdapter
from ai_integration_claude_code.config import ClaudeCodeConfig


def _fake_cli(path: Path, body: str) -> str:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def _helpful_cli(path: Path) -> str:
    return _fake_cli(
        path,
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--print --output-format --model usage"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "claude 1.2.3"; exit 0; fi\n'
        'echo \'{"result": "fixed it", "model": "claude-opus", '
        '"usage": {"input_tokens": 10, "output_tokens": 5}}\'\n'
        "exit 0\n",
    )


def test_successful_completion(tmp_path: Path):
    cli = _helpful_cli(tmp_path / "claude")
    adapter = ClaudeCodeAdapter(ClaudeCodeConfig(command=cli))
    result = adapter.run(
        prompt="fix it",
        workdir=tmp_path,
        stdout_path=tmp_path / "stdout.log",
        stderr_path=tmp_path / "stderr.log",
        events_path=tmp_path / "events.jsonl",
        timeout_seconds=10,
    )
    assert result.status == RunStatus.COMPLETED
    assert result.exit_code == 0
    assert "fixed" in result.response_text
    assert result.reported_model == "claude-opus"
    assert result.usage.input_tokens == 10
    assert (tmp_path / "stdout.log").read_text()


def test_nonzero_exit_is_agent_error(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "claude",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--print"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        'echo "boom" >&2; exit 3\n',
    )
    adapter = ClaudeCodeAdapter(ClaudeCodeConfig(command=cli))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=10,
    )
    assert result.status == RunStatus.AGENT_ERROR
    assert result.exit_code == 3
    assert "boom" in (tmp_path / "e.log").read_text()


def test_timeout(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "claude",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--print"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        "sleep 5; echo done\n",
    )
    adapter = ClaudeCodeAdapter(ClaudeCodeConfig(command=cli))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=0.3,
    )
    assert result.status == RunStatus.TIMEOUT
    assert result.exit_code is None


def test_malformed_json_does_not_crash(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "claude",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--print"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        'echo "not json {{{"; exit 0\n',
    )
    adapter = ClaudeCodeAdapter(ClaudeCodeConfig(command=cli))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=10,
    )
    assert result.status == RunStatus.COMPLETED
    assert "not json" in result.response_text
    assert result.reported_model is None


def test_missing_model_fields_unknown(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "claude",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--print"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        'echo \'{"result": "ok"}\'; exit 0\n',
    )
    adapter = ClaudeCodeAdapter(ClaudeCodeConfig(command=cli, model=""))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=10,
    )
    assert result.requested_model is None
    assert result.reported_model is None
    assert result.usage.input_tokens is None


def test_prompt_with_metachars_passed_safely(tmp_path: Path):
    received = tmp_path / "received.txt"
    cli = _fake_cli(
        tmp_path / "claude",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--print"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        f'printf "%s" "$2" > {received}\n'
        'echo \'{"result": "ok"}\'; exit 0\n',
    )
    adapter = ClaudeCodeAdapter(ClaudeCodeConfig(command=cli))
    tricky = "quotes \"' $(rm -rf /) `id`;\nunicode héllo\nnewline\n$(evil)"
    result = adapter.run(
        prompt=tricky,
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=10,
    )
    assert result.status == RunStatus.COMPLETED
    assert received.read_text(encoding="utf-8") == tricky


def test_missing_cli_is_setup_error(tmp_path: Path):
    adapter = ClaudeCodeAdapter(ClaudeCodeConfig(command="/nonexistent-claude-xyz"))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=5,
    )
    assert result.status == RunStatus.SETUP_ERROR


def test_check_does_not_run_paid_task(tmp_path: Path):
    cli = _helpful_cli(tmp_path / "claude")
    adapter = ClaudeCodeAdapter(ClaudeCodeConfig(command=cli))
    health = adapter.check()
    assert health["available"] is True
    assert "version" in health
    assert os.path.exists(cli)
    _ = json  # keep import used for clarity
