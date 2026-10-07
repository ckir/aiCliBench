"""Deterministic eval runner over the agent runtime with fake models."""

from __future__ import annotations

from collections.abc import Sequence

from ai_agents import AgentConfig, run_agent
from ai_evals.cases import EvalCase, EvalResult
from ai_plugins_sdk import Plugin, PluginRegistry
from ai_runtime.models import ChatModel


async def run_eval_case(
    case: EvalCase,
    model: ChatModel,
    plugins: Sequence[Plugin] | PluginRegistry,
    *,
    config: AgentConfig | None = None,
) -> EvalResult:
    cfg = config or AgentConfig(max_steps=case.max_steps)
    result = await run_agent(model, plugins, case.user_message, config=cfg)
    tools_used: list[str] = []
    for event in result.trace:
        tools_used.extend(event.get("tool_calls", []))
        if event.get("authorization_denied"):
            tools_used.append(str(event["authorization_denied"]))

    passed = True
    notes: list[str] = []
    if case.expected_contains is not None and case.expected_contains not in result.answer:
        passed = False
        notes.append(f"answer missing {case.expected_contains!r}")
    if case.expected_tool is not None and case.expected_tool not in tools_used:
        passed = False
        notes.append(f"expected tool {case.expected_tool!r} not used")

    return EvalResult(
        case_id=case.id,
        passed=passed,
        answer=result.answer,
        expected_contains=case.expected_contains,
        expected_tool=case.expected_tool,
        tools_used=tools_used,
        model=model.model_name,
        provider=model.provider,
        config={"max_steps": cfg.max_steps, "run_id": result.run_id},
        details="; ".join(notes),
    )


async def run_eval_suite(
    cases: Sequence[EvalCase],
    model: ChatModel,
    plugins: Sequence[Plugin] | PluginRegistry,
) -> list[EvalResult]:
    results: list[EvalResult] = []
    for case in cases:
        results.append(await run_eval_case(case, model, plugins))
    return results


def summarize(results: Sequence[EvalResult]) -> dict[str, object]:
    passed = sum(1 for r in results if r.passed)
    return {"total": len(results), "passed": passed, "failed": len(results) - passed}
