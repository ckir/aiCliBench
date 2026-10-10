"""CLI-agent adapter contract (§8). Business logic stays out of MCP/HTTP layers."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ai_core.status import ErrorCategory, RunStatus
from ai_schemas.codebench import (
    PROMPT_WRAPPER_PREAMBLE,
    PROMPT_WRAPPER_VERSION,
    AgentCapability,
    UsageRecord,
)


@dataclass(frozen=True, slots=True)
class RunResult:
    """Outcome of one agent process execution (not the evaluator verdict)."""

    agent_name: str
    requested_model: str | None
    reported_model: str | None
    cli_version: str | None
    status: RunStatus
    exit_code: int | None
    started_at: str
    ended_at: str
    elapsed_seconds: float
    response_text: str
    stdout_path: str
    stderr_path: str
    events_path: str | None
    usage: UsageRecord
    error_category: ErrorCategory | None
    error_message: str | None


class AgentAdapter(Protocol):
    """Common interface implemented by Claude Code and Antigravity adapters."""

    @property
    def agent_name(self) -> str: ...

    @property
    def capability(self) -> AgentCapability: ...

    def version(self) -> str | None:
        """Return CLI version or None when unavailable."""
        ...

    def check(self) -> dict[str, object]:
        """Non-destructive health probe (no paid/state-changing tasks)."""
        ...

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
        """Execute the agent subprocess; enforce timeout; never use shell strings."""
        ...


def wrap_prompt(instruction: str) -> str:
    """Return the identical wrapper bytes sent to every agent (§7.2)."""
    return f"{PROMPT_WRAPPER_PREAMBLE}\n\n{instruction}"


def prompt_wrapper_version() -> str:
    return PROMPT_WRAPPER_VERSION


def sha256_text(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def paired_order(agent_names: list[str], *, seed: int, pair_key: str) -> list[str]:
    """Randomize agent order per paired task/repetition with a recorded seed (§10).

    Deterministic for a given (seed, pair_key); each pair shuffles independently.
    """
    digest = hashlib.sha256(f"{seed}:{pair_key}".encode()).digest()
    local_seed = int.from_bytes(digest[:8], "big")
    rng = random.Random(local_seed)  # noqa: S311 - deterministic shuffle, not crypto
    order = list(agent_names)
    rng.shuffle(order)
    return order


def categorize_exit(
    *, exit_code: int | None, timed_out: bool, interrupted: bool
) -> tuple[RunStatus, ErrorCategory | None]:
    """Map process outcome to (status, error_category)."""
    if interrupted:
        return RunStatus.INTERRUPTED, ErrorCategory.INTERRUPTED
    if timed_out:
        return RunStatus.TIMEOUT, ErrorCategory.TIMEOUT
    if exit_code is None:
        return RunStatus.AGENT_ERROR, ErrorCategory.AGENT_ERROR
    if exit_code == 0:
        return RunStatus.COMPLETED, None
    return RunStatus.AGENT_ERROR, ErrorCategory.AGENT_ERROR
