"""Deterministic evaluation cases and results (no live providers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class EvalCase:
    """A reproducible eval: input, expectation rubric, and agent budget."""

    id: str
    description: str
    user_message: str
    expected_contains: str | None = None
    expected_tool: str | None = None
    max_steps: int = 5


@dataclass(frozen=True, slots=True)
class EvalResult:
    """Recorded outcome with enough metadata to reproduce the run."""

    case_id: str
    passed: bool
    answer: str
    expected_contains: str | None
    expected_tool: str | None
    tools_used: list[str]
    model: str
    provider: str
    config: dict[str, Any] = field(default_factory=dict)
    details: str = ""
