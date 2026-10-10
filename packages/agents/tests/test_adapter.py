from pathlib import Path

from ai_agents import (
    categorize_exit,
    paired_order,
    sha256_text,
    wrap_prompt,
)
from ai_core.status import ErrorCategory, RunStatus
from ai_schemas.codebench import PROMPT_WRAPPER_VERSION


def test_wrap_prompt_identical_and_versioned():
    first = wrap_prompt("do X")
    second = wrap_prompt("do X")
    assert first == second
    assert PROMPT_WRAPPER_VERSION.startswith("codebench-")
    assert "do X" in first


def test_sha256_stable():
    assert sha256_text("abc") == sha256_text("abc")
    assert sha256_text("abc") != sha256_text("abd")


def test_paired_order_reproducible():
    agents = ["claude", "antigravity"]
    first = paired_order(agents, seed=42, pair_key="task:1")
    second = paired_order(agents, seed=42, pair_key="task:1")
    assert first == second
    assert sorted(first) == sorted(agents)
    # Different pair keys may shuffle differently but stay deterministic.
    third = paired_order(agents, seed=42, pair_key="task:2")
    assert sorted(third) == sorted(agents)
    assert paired_order(agents, seed=99, pair_key="task:1") == paired_order(
        agents, seed=99, pair_key="task:1"
    )


def test_categorize_exit():
    status, cat = categorize_exit(exit_code=0, timed_out=False, interrupted=False)
    assert status == RunStatus.COMPLETED
    assert cat is None

    status, cat = categorize_exit(exit_code=1, timed_out=False, interrupted=False)
    assert status == RunStatus.AGENT_ERROR
    assert cat == ErrorCategory.AGENT_ERROR

    status, _ = categorize_exit(exit_code=None, timed_out=True, interrupted=False)
    assert status == RunStatus.TIMEOUT

    status, _ = categorize_exit(exit_code=None, timed_out=False, interrupted=True)
    assert status == RunStatus.INTERRUPTED


def test_runresult_importable():
    from ai_agents.adapter import RunResult

    assert RunResult is not None
    _ = Path
