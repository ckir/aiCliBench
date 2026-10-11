"""Generic CLI adapter implementing AgentAdapter protocol."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from ai_agents.adapter import RunResult, categorize_exit
from ai_core.errors import ConfigurationError
from ai_core.status import ErrorCategory, RunStatus
from ai_integration_generic_cli.config import GenericCliConfig
from ai_schemas.codebench import AgentCapability, UsageRecord


def _parse_output(
    stdout: str, fmt: str
) -> tuple[str, str | None, UsageRecord]:
    """Parse CLI output based on format."""
    if fmt == "json":
        try:
            payload = json.loads(stdout.strip())
            if isinstance(payload, dict):
                response = str(
                    payload.get("result", payload.get("content", payload.get("text", "")))
                )
                model = payload.get("model", payload.get("model_name"))
                usage = UsageRecord()
                if isinstance(payload.get("usage"), dict):
                    raw = payload["usage"]
                    usage = UsageRecord(
                        input_tokens=raw.get("input_tokens"),
                        output_tokens=raw.get("output_tokens"),
                        cache_tokens=raw.get("cache_tokens"),
                        total_tokens=raw.get("total_tokens"),
                        cost_usd=raw.get("cost_usd"),
                        raw={k: v for k, v in raw.items() if isinstance(v, (int, float, str))},
                    )
                return response, model, usage
        except (json.JSONDecodeError, ValueError):
            pass
    elif fmt == "jsonl":
        response_parts: list[str] = []
        reported_model: str | None = None
        usage = UsageRecord()
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(event, dict):
                continue
            kind = str(event.get("type", event.get("event", ""))).lower()
            # For jsonl, we take the last result/completion/message/text event
            if kind in ("result", "completion", "message", "text") and event.get("text"):
                response_parts = [str(event["text"])]
            elif isinstance(event.get("content"), str) and event["content"]:
                response_parts = [str(event["content"])]
            if isinstance(event.get("model"), str) and event["model"]:
                reported_model = str(event["model"])
            if isinstance(event.get("usage"), dict):
                raw = event["usage"]
                usage = UsageRecord(
                    input_tokens=raw.get("input_tokens"),
                    output_tokens=raw.get("output_tokens"),
                    cache_tokens=raw.get("cache_tokens"),
                    total_tokens=raw.get("total_tokens"),
                    cost_usd=raw.get("cost_usd"),
                    raw={k: v for k, v in raw.items() if isinstance(v, (int, float, str))},
                )
        response = "\n".join(response_parts)[:20000] if response_parts else stdout[:8000]
        return response, reported_model, usage
    # text mode - strip trailing newline
    return stdout.rstrip("\n"), None, UsageRecord()


class GenericCliAdapter:
    """Subprocess adapter for a generic CLI agent."""

    def __init__(self, name: str, config: GenericCliConfig) -> None:
        self._name = name
        self._config = config
        self._help_cache: str | None = None

    @property
    def agent_name(self) -> str:
        return self._name

    @property
    def capability(self) -> AgentCapability:
        help_text = self._help()
        has_model_flag = bool(self._config.model_flag) and self._config.model_flag in help_text
        has_output_format = "--output-format" in help_text
        has_usage = "usage" in help_text.lower()
        return AgentCapability(
            agent_name=self._name,
            non_interactive=True,
            model_selection=has_model_flag,
            structured_output=self._config.output_format != "text",
            reported_model=bool(self._config.model),
            usage_telemetry=has_usage,
            reported_cost=False,
            timeout_enforcement=True,
            cancellation=True,
        )

    def _help(self) -> str:
        if self._help_cache is None:
            try:
                result = subprocess.run(  # noqa: S603
                    [self._config.command, "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self._help_cache = (result.stdout or "") + "\n" + (result.stderr or "")
            except (OSError, subprocess.SubprocessError):
                self._help_cache = ""
        return self._help_cache

    def version(self) -> str | None:
        for flag in self._config.version_args:
            try:
                result = subprocess.run(  # noqa: S603
                    [self._config.command, flag],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    text = (result.stdout or result.stderr or "").strip()
                    if text:
                        return text.splitlines()[0].strip()
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def check(self) -> dict[str, object]:
        command = self._config.command
        available = shutil.which(command) is not None
        return {
            "agent": self._name,
            "available": available,
            "command": command,
            "version": self.version() if available else None,
            "capability": self.capability.model_dump(),
        }

    def build_argv(self, prompt: str) -> list[str]:
        """Build arg list with prompt substitution."""
        help_text = self._help()
        argv: list[str] = [self._config.command]
        # Substitute {prompt} placeholders in args
        prompt_substituted = False
        for arg in self._config.args:
            if "{prompt}" in arg:
                argv.append(arg.replace("{prompt}", prompt))
                prompt_substituted = True
            else:
                argv.append(arg)
        # Add output format before prompt (if no placeholder)
        if has_output_format := ("--output-format" in help_text) and self._config.output_format:
            argv += ["--output-format", self._config.output_format]
        # Add model flag before prompt (if no placeholder)
        if self._config.model and self._config.model_flag and self._config.model_flag in help_text:
            argv += [self._config.model_flag, self._config.model]
        if not prompt_substituted:
            argv.append(prompt)
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
                agent_name=self._name,
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
                error_message=f"CLI not found: {self._config.command!r}",
            )
        argv = self.build_argv(prompt)
        try:
            completed = subprocess.run(  # noqa: S603
                argv,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - begin
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stdout_path.write_text(stdout, encoding="utf-8")
            stderr_path.write_text(stderr, encoding="utf-8")
            status, category = categorize_exit(exit_code=None, timed_out=True, interrupted=False)
            return RunResult(
                agent_name=self._name,
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
                agent_name=self._name,
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
        response, reported_model, usage = _parse_output(
            completed.stdout or "", self._config.output_format
        )
        response_redacted, _ = _redact(response)
        status, category = categorize_exit(
            exit_code=completed.returncode, timed_out=False, interrupted=False
        )
        requested = self._config.model or None
        # If model was requested but CLI doesn't support model flag, don't report
        if requested and self._config.model_flag not in self._help():
            reported_model = None
        message: str | None = None
        if status != RunStatus.COMPLETED:
            message = (completed.stderr or "")[:2000] or None
        return RunResult(
            agent_name=self._name,
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