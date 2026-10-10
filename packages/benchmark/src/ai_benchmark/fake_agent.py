"""Fake CLI-agent for integration tests (no provider calls, no network)."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from ai_agents.adapter import categorize_exit
from ai_benchmark.redaction import redact_text
from ai_core.status import ErrorCategory, RunStatus
from ai_schemas.codebench import AgentCapability, UsageRecord

FakeMode = Literal["pass", "fail", "error", "timeout"]


class FakeAgentAdapter:
    """Writes a deterministic patch into the workspace instead of calling a model."""

    def __init__(
        self,
        agent_name: str = "fake",
        mode: FakeMode = "pass",
        *,
        version: str = "fake-0.1.0",
        patch_text: str | None = None,
    ) -> None:
        self._name = agent_name
        self._mode = mode
        self._version = version
        self._patch_text = patch_text

    @property
    def agent_name(self) -> str:
        return self._name

    @property
    def capability(self) -> AgentCapability:
        return AgentCapability(
            agent_name=self._name,
            non_interactive=True,
            model_selection=True,
            structured_output=True,
            reported_model=True,
            usage_telemetry=True,
            reported_cost=False,
            timeout_enforcement=True,
            cancellation=True,
        )

    def version(self) -> str | None:
        return self._version

    def check(self) -> dict[str, object]:
        return {
            "agent": self._name,
            "available": True,
            "version": self._version,
            "capability": self.capability.model_dump(),
        }

    def _write_patch(self, workdir: Path) -> str:
        target = workdir / "calc.py"
        if self._mode == "pass":
            text = "def add(a, b):\n    return a + b\n"
        elif self._mode == "fail":
            text = "def add(a, b):\n    return a - b  # still buggy\n"
        elif self._mode == "error":
            raise RuntimeError("fake agent exploded")
        else:  # timeout handled by caller sleeping
            text = "def add(a, b):\n    return a - b\n"
        if self._patch_text is not None:
            text = self._patch_text
        target.write_text(text, encoding="utf-8")
        return text

    def run(
        self,
        *,
        prompt: str,
        workdir: Path,
        stdout_path: Path,
        stderr_path: Path,
        events_path: Path | None,
        timeout_seconds: float,
    ) -> object:
        """Execute fake work; returns RunResult (typed as object to avoid import cycle)."""
        from ai_agents.adapter import RunResult

        started = datetime.now(UTC).isoformat()
        begin = time.monotonic()
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if self._mode == "timeout":
                time.sleep(timeout_seconds + 0.2)
                elapsed = time.monotonic() - begin
                status, category = categorize_exit(
                    exit_code=None, timed_out=True, interrupted=False
                )
                stdout_path.write_text("fake: timed out\n", encoding="utf-8")
                stderr_path.write_text("", encoding="utf-8")
                response, _ = redact_text("fake timeout")
                return RunResult(
                    agent_name=self._name,
                    requested_model="fake-test",
                    reported_model="fake-test",
                    cli_version=self._version,
                    status=status,
                    exit_code=None,
                    started_at=started,
                    ended_at=datetime.now(UTC).isoformat(),
                    elapsed_seconds=elapsed,
                    response_text=response,
                    stdout_path=str(stdout_path),
                    stderr_path=str(stderr_path),
                    events_path=str(events_path) if events_path else None,
                    usage=UsageRecord(),
                    error_category=category,
                    error_message="fake timeout exceeded",
                )
            response_text = self._write_patch(workdir)
            elapsed = time.monotonic() - begin
            status, category = categorize_exit(exit_code=0, timed_out=False, interrupted=False)
            stdout_path.write_text(f"fake {self._mode}: wrote calc.py\n", encoding="utf-8")
            stderr_path.write_text("", encoding="utf-8")
            if events_path is not None:
                events_path.write_text('{"event": "done"}\n', encoding="utf-8")
            response, _ = redact_text(response_text)
            return RunResult(
                agent_name=self._name,
                requested_model="fake-test",
                reported_model="fake-test",
                cli_version=self._version,
                status=status,
                exit_code=0,
                started_at=started,
                ended_at=datetime.now(UTC).isoformat(),
                elapsed_seconds=elapsed,
                response_text=response,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                events_path=str(events_path) if events_path else None,
                usage=UsageRecord(),
                error_category=category,
                error_message=None,
            )
        except Exception as exc:
            elapsed = time.monotonic() - begin
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text(f"fake error: {exc}\n", encoding="utf-8")
            return RunResult(
                agent_name=self._name,
                requested_model="fake-test",
                reported_model=None,
                cli_version=self._version,
                status=RunStatus.AGENT_ERROR,
                exit_code=1,
                started_at=started,
                ended_at=datetime.now(UTC).isoformat(),
                elapsed_seconds=elapsed,
                response_text="",
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                events_path=str(events_path) if events_path else None,
                usage=UsageRecord(),
                error_category=ErrorCategory.AGENT_ERROR,
                error_message=str(exc),
            )
