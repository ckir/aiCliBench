"""Antigravity (`agy`) CLI adapter (§8.3).

Uses non-interactive/print mode when supported; prefers documented JSON or
streaming JSON; captures the raw event stream and parses recognized result,
completion, usage, and error events defensively.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from ai_agents.adapter import RunResult, categorize_exit
from ai_core.status import ErrorCategory, RunStatus
from ai_integration_antigravity.config import AntigravityConfig
from ai_schemas.codebench import AgentCapability, UsageRecord


def _help_text(command: str) -> str:
    """Get the help text from a CLI command.

    Args:
        command: The command to query (e.g., "agy").

    Returns:
        Combined stdout and stderr from the command's --help output,
        or empty string if the command fails.
    """
    try:
        result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
            [command, "--help"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return (result.stdout or "") + "\n" + (result.stderr or "")


def _version_text(command: str) -> str | None:
    """Get the version string from a CLI command.

    Args:
        command: The command to query (e.g., "agy").

    Returns:
        The first line of version output, or None if unavailable.
    """
    for flag in ("--version", "version"):
        try:
            result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
                [command, flag], capture_output=True, text=True, timeout=10
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            text = (result.stdout or result.stderr or "").strip()
            if text:
                return text.splitlines()[0].strip()
    return None


def _parse_stream(stdout: str) -> tuple[str, str | None, UsageRecord, str | None]:
    """Parse stream-json events; unknown/malformed events are skipped.

    Args:
        stdout: Raw stdout from the CLI process.

    Returns:
        Tuple of (response_text, reported_model, usage_record, error_message).
    """
    response_parts: list[str] = []
    reported: str | None = None
    usage = UsageRecord()
    error: str | None = None
    tried_json = False
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            tried_json = True
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(event, dict):
            continue
        kind = str(event.get("type", event.get("event", ""))).lower()
        if kind in ("result", "completion", "message", "text") and event.get("text"):
            response_parts.append(str(event["text"]))
        elif isinstance(event.get("content"), str) and event["content"]:
            response_parts.append(str(event["content"]))
        if isinstance(event.get("model"), str) and event["model"]:
            reported = str(event["model"])
        if isinstance(event.get("usage"), dict):
            raw = event["usage"]
            with suppress(Exception):
                usage = UsageRecord(
                    input_tokens=raw.get("input_tokens"),
                    output_tokens=raw.get("output_tokens"),
                    cache_tokens=raw.get("cache_tokens"),
                    total_tokens=raw.get("total_tokens"),
                    cost_usd=raw.get("cost_usd"),
                    raw={k: v for k, v in raw.items() if isinstance(v, (int, float, str))},
                )
        if kind in ("error", "failure") and event.get("error"):
            error = str(event["error"])[:2000]
    if not tried_json:
        # Fall back to single JSON object or raw text.
        try:
            payload = json.loads(stdout.strip())
            if isinstance(payload, dict):
                content = payload.get("result", payload.get("content", ""))
                if content:
                    response_parts.append(str(content))
                if isinstance(payload.get("model"), str):
                    reported = str(payload["model"])
        except (json.JSONDecodeError, ValueError):
            pass
    response = "\n".join(response_parts)[:20000] if response_parts else stdout[:8000]
    return response, reported, usage, error


class AntigravityAdapter:
    """Subprocess adapter for the Google Antigravity CLI (`agy`).

    Implements the AgentAdapter protocol for the Google Antigravity CLI.
    Uses non-interactive/print mode when supported; prefers documented JSON
    or streaming JSON; captures the raw event stream and parses recognized
    result, completion, usage, and error events defensively.
    """

    def __init__(self, config: AntigravityConfig | None = None) -> None:
        """Initialize the adapter.

        Args:
            config: Adapter configuration. Uses defaults if not provided.
        """
        self._config = config or AntigravityConfig()
        self._help_cache: str | None = None

    @property
    def agent_name(self) -> str:
        """Return the agent identifier."""
        return "antigravity"

    @property
    def capability(self) -> AgentCapability:
        """Return the adapter's capabilities by probing the CLI's --help.

        Returns:
            AgentCapability with feature flags based on supported CLI flags.
        """
        help_text = self._help()
        return AgentCapability(
            agent_name="antigravity",
            non_interactive="-p" in help_text or "--print" in help_text,
            model_selection="--model" in help_text,
            structured_output="--output-format" in help_text,
            reported_model=True,
            usage_telemetry="usage" in help_text.lower(),
            reported_cost=False,
            timeout_enforcement=True,
            cancellation=True,
        )

    def _help(self) -> str:
        """Get and cache the CLI's help text."""
        if self._help_cache is None:
            self._help_cache = _help_text(self._config.command)
        return self._help_cache

    def version(self) -> str | None:
        """Get the CLI version string.

        Returns:
            Version string from `agy --version` or `agy version`,
            or None if unavailable.
        """
        return _version_text(self._config.command)

    def check(self) -> dict[str, object]:
        """Non-destructive health probe (no paid/state-changing tasks).

        Returns:
            Dictionary with keys: agent, available, command, version, capability.
        """
        command = self._config.command
        available = shutil.which(command) is not None
        return {
            "agent": "antigravity",
            "available": available,
            "command": command,
            "version": self.version() if available else None,
            "capability": self.capability.model_dump(),
        }

    def build_argv(self, prompt: str) -> list[str]:
        """Build arg list with documented prompt mechanism (no shell concat).

        Args:
            prompt: The prompt to send to the agent.

        Returns:
            List of command-line arguments.
        """
        help_text = self._help()
        argv: list[str] = [self._config.command]
        if "-p" in help_text:
            argv += ["-p", prompt]
        else:
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
        """Execute the agent subprocess; enforce timeout; never use shell strings.

        Args:
            prompt: The prompt to send to the agent.
            workdir: Working directory for the subprocess.
            stdout_path: File path to capture stdout.
            stderr_path: File path to capture stderr.
            events_path: Optional file path for event stream (JSONL).
            timeout_seconds: Maximum execution time in seconds.

        Returns:
            RunResult with execution outcome and captured output.
        """
        from ai_benchmark.redaction import redact_text as _redact

        started_at = datetime.now(UTC).isoformat()
        begin = time.monotonic()
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        if shutil.which(self._config.command) is None:
            elapsed = time.monotonic() - begin
            return RunResult(
                agent_name="antigravity",
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
                error_message=f"agy CLI not found: {self._config.command!r}",
            )
        argv = self.build_argv(prompt)
        try:
            completed = subprocess.run(  # noqa: S603 - fixed arg list, no shell
                argv, cwd=str(workdir), capture_output=True, text=True, timeout=timeout_seconds
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - begin
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stdout_path.write_text(stdout, encoding="utf-8")
            stderr_path.write_text(stderr, encoding="utf-8")
            status, category = categorize_exit(exit_code=None, timed_out=True, interrupted=False)
            return RunResult(
                agent_name="antigravity",
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
                agent_name="antigravity",
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
        response, reported_model, usage, stream_error = _parse_stream(completed.stdout or "")
        response_redacted, _ = _redact(response)
        status, category = categorize_exit(
            exit_code=completed.returncode, timed_out=False, interrupted=False
        )
        requested = self._config.model or None
        if requested and "--model" not in self._help():
            reported_model = None
        message: str | None = None
        if status != RunStatus.COMPLETED:
            message = stream_error or (completed.stderr or "")[:2000] or None
        return RunResult(
            agent_name="antigravity",
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
            error_message=message,
        )
