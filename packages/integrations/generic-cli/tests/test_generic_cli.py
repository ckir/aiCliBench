"""Generic CLI adapter tests with fake executables."""

import stat
from pathlib import Path

from ai_core.status import RunStatus
from ai_integration_generic_cli.adapter import GenericCliAdapter
from ai_integration_generic_cli.config import GenericCliConfig


def _fake_cli(path: Path, body: str) -> str:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def _helpful_cli(path: Path) -> str:
    return _fake_cli(
        path,
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--output-format --model usage"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "generic-cli 1.0"; exit 0; fi\n'
        'echo \'{"result": "fixed it", "model": "generic-model", '
        '"usage": {"input_tokens": 10, "output_tokens": 5}}\'\n'
        "exit 0\n",
    )


def test_json_output_parsed(tmp_path: Path):
    cli = _helpful_cli(tmp_path / "mycli")
    adapter = GenericCliAdapter("mycli", GenericCliConfig(command=cli, output_format="json"))
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
    assert result.reported_model == "generic-model"
    assert result.usage.input_tokens == 10
    assert (tmp_path / "stdout.log").read_text()


def test_jsonl_last_object_wins(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "mycli",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--output-format"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        'echo \'{"type": "text", "text": "first"}\'\n'
        'echo \'{"type": "result", "text": "last", "model": "m1"}\'\n'
        "exit 0\n",
    )
    adapter = GenericCliAdapter("mycli", GenericCliConfig(command=cli, output_format="jsonl"))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=10,
    )
    assert result.status == RunStatus.COMPLETED
    assert "last" in result.response_text
    assert "first" not in result.response_text
    assert result.reported_model == "m1"


def test_text_mode_raw(tmp_path: Path):
    cli = _fake_cli(
        tmp_path / "mycli",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo ""; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        'echo "raw text output"\n'
        "exit 0\n",
    )
    adapter = GenericCliAdapter("mycli", GenericCliConfig(command=cli, output_format="text"))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=10,
    )
    assert result.status == RunStatus.COMPLETED
    assert result.response_text == "raw text output"
    assert result.reported_model is None


def test_prompt_placeholder_substituted(tmp_path: Path):
    received = tmp_path / "received.txt"
    cli = _fake_cli(
        tmp_path / "mycli",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--output-format"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        f'printf "%s" "$2" > {received}\n'
        'echo \'{"result": "ok"}\'; exit 0\n',
    )
    adapter = GenericCliAdapter(
        "mycli", GenericCliConfig(command=cli, args=["--ask", "{prompt}", "--quiet"])
    )
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


def test_prompt_appended_when_no_placeholder(tmp_path: Path):
    received = tmp_path / "received.txt"
    cli = _fake_cli(
        tmp_path / "mycli",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo ""; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        # Prompt is the last argument (after --output-format)
        'printf "%s" "$' + '{@: -1}" > ' + str(received) + "\n"
        'echo \'{"result": "ok"}\'; exit 0\n',
    )
    adapter = GenericCliAdapter("mycli", GenericCliConfig(command=cli, args=["--quiet"]))
    result = adapter.run(
        prompt="hello world",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=10,
    )
    assert result.status == RunStatus.COMPLETED
    assert received.read_text(encoding="utf-8") == "hello world"


def test_model_flag_appended(tmp_path: Path):
    received = tmp_path / "received.txt"
    cli = _fake_cli(
        tmp_path / "mycli",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo "--model --output-format"; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        # argv: --quiet --model my-model <prompt>; the model value is $3
        f'printf "%s" "$3" > {received}\n'
        'echo \'{"result": "ok"}\'; exit 0\n',
    )
    adapter = GenericCliAdapter(
        "mycli",
        GenericCliConfig(command=cli, model="my-model", model_flag="--model", args=["--quiet"]),
    )
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=10,
    )
    assert result.status == RunStatus.COMPLETED
    assert received.read_text(encoding="utf-8") == "my-model"


def test_timeout_and_missing_cli(tmp_path: Path):
    # Missing CLI
    adapter = GenericCliAdapter("mycli", GenericCliConfig(command="/nonexistent-cli"))
    result = adapter.run(
        prompt="x",
        workdir=tmp_path,
        stdout_path=tmp_path / "o.log",
        stderr_path=tmp_path / "e.log",
        events_path=None,
        timeout_seconds=5,
    )
    assert result.status == RunStatus.SETUP_ERROR
    assert "not found" in (result.error_message or "")

    # Timeout
    cli = _fake_cli(
        tmp_path / "mycli",
        "#!/bin/bash\n"
        'if [ "$1" = "--help" ]; then echo ""; exit 0; fi\n'
        'if [ "$1" = "--version" ]; then echo "1.0"; exit 0; fi\n'
        "sleep 5; echo done\n",
    )
    adapter = GenericCliAdapter("mycli", GenericCliConfig(command=cli))
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
