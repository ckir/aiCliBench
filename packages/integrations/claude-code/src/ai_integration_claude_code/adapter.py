"""Claude Code CLI adapter (§8.2).

Non-interactive/print mode with defensive structured-output parsing.
Verifies flags against `claude --help`; never assumes JSON fields exist.
No permission-bypass flags by default; container boundary is isolation.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from ai_agents.adapter import RunResult, categorize_exit
from ai_core.status import ErrorCategory, RunStatus
from ai_integration_claude_code.config import ClaudeCodeConfig
from ai_schemas.codebench import AgentCapability, UsageRecord


def _help_text(command: str) -> str:
    try:
        result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
            [command, "--help"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return (result.stdout or "") + "\n" + (result.stderr or "")


def _version_text(command: str) -> str | None:
    try:
        result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
            [command, "--version"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    text = (result.stdout or result.stderr or "").strip()
    return text.splitlines()[0].strip() if text else None


def _parse_usage(payload: object) -> UsageRecord:
    """Extract known usage fields only; unknown/missing → None (§12.3)."""
    if not isinstance(payload, dict):
        return UsageRecord()
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else payload
    if not isinstance(usage, dict):
        return UsageRecord()

    def _int(key: str) -> int | None:
        for candidate in (key, f"{key}_tokens"):
            value = usage.get(candidate)
            if isinstance(value, (int, float)) and value >= 0:
                return int(value)
        return None

    cost = usage.get("cost_usd", usage.get("cost"))
    cost_value = float(cost) if isinstance(cost, (int, float)) and cost >= 0 else None
    try:
        return UsageRecord(
            input_tokens=_int("input"),
            output_tokens=_int("output"),
            cache_tokens=_int("cache"),
            total_tokens=_int("total"),
            cost_usd=cost_value,
            raw={k: v for k, v in usage.items() if isinstance(v, (int, float, str))},
        )
    except Exception:
        return UsageRecord()


def _parse_response(stdout: str) -> tuple[str, str | None, UsageRecord]:
    """Defensively parse structured output; malformed events never crash."""
    text = stdout.strip()
    if not text:
        return "", None, UsageRecord()
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Try JSONL: last parseable object wins.
        payload = None
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
        if payload is None:
            return text[:8000], None, UsageRecord()
    if not isinstance(payload, dict):
        return text[:8000], None, UsageRecord()
    content = payload.get("result", payload.get("content", payload.get("text", "")))
    response = str(content)[:20000] if content else text[:8000]
    reported = payload.get("model", payload.get("model_name"))
    reported_model = str(reported) if isinstance(reported, str) and reported else None
    return response, reported_model, _parse_usage(payload)


class ClaudeCodeAdapter:
    """Subprocess adapter for the Claude Code CLI."""

    def __init__(self, config: ClaudeCodeConfig | None = None) -> None:
        self._config = config or ClaudeCodeConfig()
        self._help_cache: str | None = None

    @property
    def agent_name(self) -> str:
        return "claude"

    @property
    def capability(self) -> AgentCapability:
        help_text = self._help()
        return AgentCapability(
            agent_name="claude",
            non_interactive="--print" in help_text or "-p" in help_text,
            model_selection="--model" in help_text,
            structured_output="--output-format" in help_text,
            reported_model=True,
            usage_telemetry="usage" in help_text.lower(),
            reported_cost=False,
            timeout_enforcement=True,
            cancellation=True,
        )

    def _help(self) -> str:
        if self._help_cache is None:
            self._help_cache = _help_text(self._config.command)
        return self._help_cache

    def version(self) -> str | None:
        return _version_text(self._config.command)

    def check(self) -> dict[str, object]:
        command = self._config.command
        available = shutil.which(command) is not None
        return {
            "agent": "claude",
            "available": available,
            "command": command,
            "version": self.version() if available else None,
            "capability": self.capability.model_dump(),
        }

    def build_argv(self, prompt: str) -> list[str]:
        """Build the CLI argument list (no shell). Verifies flags via --help."""
        help_text = self._help()
        argv: list[str] = [self._config.command]
        if "--print" in help_text:
            argv.append("--print")
        argv.append(prompt)
        if "--output-format" in help_text and self._config.output_format:
            argv += ["--output-format", self._config.output_format]
        if self._config.model and "--model" in help_text:
            argv += ["--model", self._config.model]
        return argv

    def run(
        self,
        *,
        prompt: str,
        workdir: Path,
        stdout_path: Path,
        stderr_path: Path,
        events_path: Path | None,
        timeout_seconds: float,
    ) -> RunResult:
        from ai_benchmark.redaction import redact_text as _redact

        started_at = datetime.now(UTC).isoformat()
        begin = time.monotonic()
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        if shutil.which(self._config.command) is None:
            elapsed = time.monotonic() - begin
            return RunResult(
                agent_name="claude",
                requested_model=self._config.model or None,
                reported_model=None,
                cli_version=None,
                status=RunStatus.SETUP_ERROR,
                exit_code=None,
                started_at=started_at,
                ended_at=datetime.now(UTC).isoformat(),
                elapsed_seconds=elapsed,
                response_text="",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                events_path=str(events_path) if events_path else None,
                usage=UsageRecord(),
                error_category=ErrorCategory.SETUP_ERROR,
                error_message=f"claude CLI not found: {self._config.command!r}",
            )
        argv = self.build_argv(prompt)
        try:
            completed = subprocess.run(  # noqa: S603 - fixed arg list, no shell
                argv,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - begin
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stdout_path.write_text(stdout, encoding="utf-8")
            stderr_path.write_text(stderr, encoding="utf-8")
            status, category = categorize_exit(exit_code=None, timed_out=True, interrupted=False)
            return RunResult(
                agent_name="claude",
                requested_model=self._config.model or None,
                reported_model=None,
                cli_version=self.version(),
                status=status,
                exit_code=None,
                started_at=started_at,
                ended_at=datetime.now(UTC).isoformat(),
                elapsed_seconds=elapsed,
                response_text="",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                events_path=str(events_path) if events_path else None,
                usage=UsageRecord(),
                error_category=category,
                error_message=f"timeout after {timeout_seconds}s",
            )
        except OSError as exc:
            elapsed = time.monotonic() - begin
            return RunResult(
                agent_name="claude",
                requested_model=self._config.model or None,
                reported_model=None,
                cli_version=None,
                status=RunStatus.SETUP_ERROR,
                exit_code=None,
                started_at=started_at,
                ended_at=datetime.now(UTC).isoformat(),
                elapsed_seconds=elapsed,
                response_text="",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                events_path=str(events_path) if events_path else None,
                usage=UsageRecord(),
                error_category=ErrorCategory.SETUP_ERROR,
                error_message=str(exc),
            )
        elapsed = time.monotonic() - begin
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        if events_path is not None:
            events_path.write_text(completed.stdout or "", encoding="utf-8")
        response, reported_model, usage = _parse_response(completed.stdout or "")
        response_redacted, _ = _redact(response)
        status, category = categorize_exit(
            exit_code=completed.returncode, timed_out=timed_out, interrupted=False
        )
        requested = self._config.model or None
        if requested and "--model" not in self._help():
            reported_model = None  # cannot pin; record as unresolved
        return RunResult(
            agent_name="claude",
            requested_model=requested,
            reported_model=reported_model,
            cli_version=self.version(),
            status=status,
            exit_code=completed.returncode,
            started_at=started_at,
            ended_at=datetime.now(UTC).isoformat(),
            elapsed_seconds=elapsed,
            response_text=response_redacted,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            events_path=str(events_path) if events_path else None,
            usage=usage,
            error_category=category,
            error_message=(
                None if status == RunStatus.COMPLETED else (completed.stderr or "")[:2000]
            ),
        )
