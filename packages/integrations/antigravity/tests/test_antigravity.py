"""Antigravity adapter tests with fake executables (no provider calls)."""

import stat
from pathlib import Path

from ai_core.status import RunStatus
from ai_integration_antigravity.adapter import AntigravityAdapter
from ai_integration_antigravity.config import AntigravityConfig


def _fake_cli(path: Path, body: str) -> str:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def test_stream_json_success(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "agy",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "-p --output-format --model usage"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "agy 0.9.0"; exit 0; fi\n'
        'echo \'{"type": "result", "text": "fixed"}\'\n'
        'echo \'{"type": "usage", "usage": {"input_tokens": 7, "output_tokens": 3}}\'\n'
        "exit 0\n",
    )
    adapter = AntigravityAdapter(AntigravityConfig(command=cli))
    result = adapter.run(
        prompt="fix",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=tmp_path / "ev.jsonl",
        timeout_seconds=10,
    )
    assert result.status == RunStatus.COMPLETED
    assert "fixed" in result.response_text
    assert result.usage.input_tokens == 7


def test_malformed_stream_skipped(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "agy",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "-p"; exit 0; fi\n'
        'echo "garbage line"\n'
        'echo \'{"type": "result", "text": "ok"}\'\n'
        'echo "{bad json"\n'
        "exit 0\n",
    )
    adapter = AntigravityAdapter(AntigravityConfig(command=cli))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=10,
    )
    assert result.status == RunStatus.COMPLETED
    assert "ok" in result.response_text


def test_timeout_and_missing_cli(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "agy",
        '#!/bin/bash\nif [ "$1" = "--help" ]; then echo "-p"; exit 0; fi\nsleep 5\n',
    )
    adapter = AntigravityAdapter(AntigravityConfig(command=cli))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=0.3,
    )
    assert result.status == RunStatus.TIMEOUT

    missing = AntigravityAdapter(AntigravityConfig(command="/nonexistent-agy-xyz"))
    result2 = missing.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o2.log",
        stderr_path=tmp_path / "e2.log",
        events_path=None,
        timeout_seconds=5,
    )
    assert result2.status.value == "setup_error"


def test_prompt_metachars_safe(tmp_path: Path):
    received = tmp_path / "received.txt"
    cli = _fake_cli(
        tmp_path / "agy",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "-p"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "agy 0.9.0"; exit 0; fi\n'
        'if [ "$1" = "version" ]; then echo "agy 0.9.0"; exit 0; fi\n'
        f'printf "%s" "$2" > {received}\n'
        'echo \'{"type": "result", "text": "ok"}\'; exit 0\n',
    )
    adapter = AntigravityAdapter(AntigravityConfig(command=cli))
    tricky = "a\"b'c $(evil) `id`; héllo\nnewline"
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


def test_argv_uses_documented_prompt_mechanism(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "agy",
        "#!/bin/bash\necho help; exit 0\n",
    )
    adapter = AntigravityAdapter(AntigravityConfig(command=cli))
    argv = adapter.build_argv("hello")
    assert argv[0] == cli
    assert "hello" in argv
    assert any(a in ("-p", "hello") for a in argv)
