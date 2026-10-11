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
    """Outcome of one agent process execution (not the evaluator verdict).

    Attributes:
        agent_name: Name of the agent (e.g., "claude", "antigravity").
        requested_model: Model name requested via configuration, if any.
        reported_model: Model name reported by the CLI, if available.
        cli_version: CLI version string from ``--version``.
        status: Process completion status.
        exit_code: Process exit code (None if timed out).
        started_at: ISO 8601 timestamp when execution started.
        ended_at: ISO 8601 timestamp when execution ended.
        elapsed_seconds: Wall-clock execution time in seconds.
        response_text: Agent's response text (redacted, truncated to 20000 chars).
        stdout_path: Path to the captured stdout log file.
        stderr_path: Path to the captured stderr log file.
        events_path: Path to the event stream log file (if any).
        usage: Token usage and cost information.
        error_category: Category of failure (if status is not COMPLETED).
        error_message: Error message from stderr (truncated to 2000 chars).
    """

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
    """Common interface implemented by CLI agent adapters (e.g., Claude Code, Antigravity).

    Adapters encapsulate the details of invoking a specific CLI tool while
    presenting a uniform interface to the benchmark runner.
    """

    @property
    def agent_name(self) -> str: ...

    @property
    def capability(self) -> AgentCapability: ...

    def version(self) -> str | None:
        """Return CLI version string or ``None`` when unavailable."""
        ...

    def check(self) -> dict[str, object]:
        """Non-destructive health probe (no paid/state-changing tasks).

        Returns:
            Dictionary with keys: agent, available, command, version, capability.
        """
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
        """Execute the agent subprocess; enforce timeout; never use shell strings.

        Args:
            prompt: The wrapped prompt to send to the agent.
            workdir: Working directory for the agent process.
            stdout_path: File path to capture stdout.
            stderr_path: File path to capture stderr.
            events_path: Optional file path for event stream (JSONL).
            timeout_seconds: Maximum execution time in seconds.

        Returns:
            RunResult with execution outcome and captured output.
        """
        ...


def wrap_prompt(instruction: str) -> str:
    """Return the identical wrapper bytes sent to every agent (§7.2).

    The wrapper prepends a standard preamble to the task instruction to ensure
    both agents receive identical context.

    Args:
        instruction: The task instruction text.

    Returns:
        The wrapped prompt string.
    """
    return f"{PROMPT_WRAPPER_PREAMBLE}\n\n{instruction}"


def prompt_wrapper_version() -> str:
    """Return the prompt wrapper version identifier."""
    return PROMPT_WRAPPER_VERSION


def sha256_text(data: str) -> str:
    """Return the SHA256 hex digest of a text string.

    Args:
        data: The input string.

    Returns:
        Hexadecimal SHA256 digest.
    """
    return hashlib.sha256(data.encode()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Return the SHA256 hex digest of a byte string.

    Args:
        data: The input bytes.

    Returns:
        Hexadecimal SHA256 digest.
    """
    return hashlib.sha256(data).hexdigest()


def paired_order(agent_names: list[str], *, seed: int, pair_key: str) -> list[str]:
    """Randomize agent order per paired task/repetition with a recorded seed (§10).

    Deterministic for a given (seed, pair_key); each pair shuffles independently.

    Args:
        agent_names: List of agent names to shuffle.
        seed: Global random seed.
        pair_key: Unique key for this task/repetition pair (e.g., "task:1").

    Returns:
        A shuffled copy of ``agent_names``.
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
    """Map process outcome to (status, error_category).

    Args:
        exit_code: Process exit code (None if timed out).
        timed_out: Whether the process timed out.
        interrupted: Whether the process was interrupted.

    Returns:
        A tuple of (RunStatus, ErrorCategory or None).
    """
    if interrupted:
        return RunStatus.INTERRUPTED, ErrorCategory.INTERRUPTED
    if timed_out:
        return RunStatus.TIMEOUT, ErrorCategory.TIMEOUT
    if exit_code is None:
        return RunStatus.AGENT_ERROR, ErrorCategory.AGENT_ERROR
    if exit_code == 0:
        return RunStatus.COMPLETED, None
    return RunStatus.AGENT_ERROR, ErrorCategory.AGENT_ERROR
