"""Metrics and scoring (§12). Denominators always shown; no opaque single number."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CorrectnessSummary:
    eligible_evaluations: int
    acceptance_passes: int
    pass_rate: float | None
    timeout_rate: float
    agent_error_rate: float
    setup_error_rate: float
    evaluation_error_rate: float


@dataclass(frozen=True, slots=True)
class PairedSummary:
    total_pairs: int
    a_wins: int
    b_wins: int
    both_pass: int
    neither_pass: int
    invalid: int
    win_rate_a: float | None  # among valid decisive pairs


@dataclass(frozen=True, slots=True)
class RuntimeSummary:
    successful_count: int
    median_success_seconds: float | None
    iqr_success_seconds: float | None
    all_completed_count: int
    timeout_count: int


@dataclass(frozen=True, slots=True)
class CostSummary:
    total_known_cost_usd: float
    success_count: int
    cost_per_success: float | None
    coverage_known: int
    coverage_total: int


@dataclass(frozen=True, slots=True)
class ScoreReport:
    by_agent: dict[str, CorrectnessSummary] = field(default_factory=dict)
    paired: PairedSummary | None = None
    runtime_by_agent: dict[str, RuntimeSummary] = field(default_factory=dict)
    cost_by_agent: dict[str, CostSummary] = field(default_factory=dict)
    quality_gates: dict[str, dict[str, int]] = field(default_factory=dict)


def _parse_usage(usage_json: str) -> dict[str, Any]:
    try:
        data = json.loads(usage_json or "{}")
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def correctness_for_agent(
    runs: list[dict[str, Any]], evaluations: dict[str, dict[str, Any]]
) -> CorrectnessSummary:
    """Eligible = completed valid evaluations; eval errors excluded from denominator."""
    eligible = 0
    passes = 0
    timeouts = 0
    agent_errors = 0
    setup_errors = 0
    eval_errors = 0
    for run in runs:
        status = str(run.get("status", ""))
        if status == "timeout":
            timeouts += 1
        elif status == "agent_error":
            agent_errors += 1
        elif status == "setup_error":
            setup_errors += 1
        evaluation = evaluations.get(str(run.get("id", "")))
        if evaluation is None:
            continue
        eval_status = str(evaluation.get("status", ""))
        if eval_status == "evaluation_error":
            eval_errors += 1
            continue
        if eval_status not in ("pass", "fail"):
            continue
        eligible += 1
        if evaluation.get("acceptance_pass") in (1, True):
            passes += 1
    denominator = max(len(runs), 1)
    return CorrectnessSummary(
        eligible_evaluations=eligible,
        acceptance_passes=passes,
        pass_rate=(passes / eligible) if eligible else None,
        timeout_rate=timeouts / denominator,
        agent_error_rate=agent_errors / denominator,
        setup_error_rate=setup_errors / denominator,
        evaluation_error_rate=eval_errors / denominator,
    )


def paired_summary(
    runs: list[dict[str, Any]],
    evaluations: dict[str, dict[str, Any]],
    agent_a: str,
    agent_b: str,
) -> PairedSummary:
    """Match runs by (task_id, repetition) pair_key; show ties separately."""
    by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    for run in runs:
        if run.get("agent_name") not in (agent_a, agent_b):
            continue
        by_pair.setdefault(str(run.get("pair_key", "")), {})[str(run.get("agent_name"))] = run
    a_wins = b_wins = both = neither = invalid = 0
    for _pair_key, members in by_pair.items():
        if agent_a not in members or agent_b not in members:
            invalid += 1
            continue
        eval_a = evaluations.get(str(members[agent_a].get("id", "")))
        eval_b = evaluations.get(str(members[agent_b].get("id", "")))
        if eval_a is None or eval_b is None:
            invalid += 1
            continue
        if (
            str(eval_a.get("status")) == "evaluation_error"
            or str(eval_b.get("status")) == "evaluation_error"
        ):
            invalid += 1
            continue
        pass_a = eval_a.get("acceptance_pass") in (1, True)
        pass_b = eval_b.get("acceptance_pass") in (1, True)
        if pass_a and not pass_b:
            a_wins += 1
        elif pass_b and not pass_a:
            b_wins += 1
        elif pass_a and pass_b:
            both += 1
        else:
            neither += 1
    total = a_wins + b_wins + both + neither + invalid
    decisive = a_wins + b_wins
    return PairedSummary(
        total_pairs=total,
        a_wins=a_wins,
        b_wins=b_wins,
        both_pass=both,
        neither_pass=neither,
        invalid=invalid,
        win_rate_a=(a_wins / decisive) if decisive else None,
    )


def _quantile_sorted(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def runtime_for_agent(
    runs: list[dict[str, Any]], evaluations: dict[str, dict[str, Any]]
) -> RuntimeSummary:
    successful: list[float] = []
    completed_count = 0
    timeout_count = 0
    for run in runs:
        status = str(run.get("status", ""))
        if status == "timeout":
            timeout_count += 1
            continue
        if status != "completed":
            continue
        completed_count += 1
        evaluation = evaluations.get(str(run.get("id", "")))
        if evaluation is None or evaluation.get("acceptance_pass") not in (1, True):
            continue
        try:
            successful.append(float(run.get("elapsed_seconds", 0.0)))
        except (TypeError, ValueError):
            continue
    median = statistics.median(successful) if successful else None
    iqr: float | None = None
    if len(successful) >= 4:
        iqr = _quantile_sorted(successful, 0.75) - _quantile_sorted(successful, 0.25)
    elif successful:
        iqr = 0.0
    return RuntimeSummary(
        successful_count=len(successful),
        median_success_seconds=median,
        iqr_success_seconds=iqr,
        all_completed_count=completed_count,
        timeout_count=timeout_count,
    )


def cost_for_agent(runs: list[dict[str, Any]]) -> CostSummary:
    total = 0.0
    known = 0
    successes_needed = 0  # filled by caller via evaluations; here count unknown
    for run in runs:
        usage = _parse_usage(str(run.get("usage_json", "{}")))
        cost = usage.get("cost_usd")
        if isinstance(cost, (int, float)) and cost >= 0:
            total += float(cost)
            known += 1
    return CostSummary(
        total_known_cost_usd=total,
        success_count=successes_needed,
        cost_per_success=None,
        coverage_known=known,
        coverage_total=len(runs),
    )


def score_experiment(runs: list[dict[str, Any]], evaluations: list[dict[str, Any]]) -> ScoreReport:
    """Score one experiment's runs (§12). Never invents missing cost/usage."""
    eval_by_run = {str(e.get("run_id")): e for e in evaluations}
    agents = sorted({str(r.get("agent_name", "")) for r in runs if r.get("agent_name")})
    by_agent: dict[str, CorrectnessSummary] = {}
    runtime_by_agent: dict[str, RuntimeSummary] = {}
    cost_by_agent: dict[str, CostSummary] = {}
    gates: dict[str, dict[str, int]] = {}
    for agent in agents:
        agent_runs = [r for r in runs if str(r.get("agent_name")) == agent]
        by_agent[agent] = correctness_for_agent(agent_runs, eval_by_run)
        runtime_by_agent[agent] = runtime_for_agent(agent_runs, eval_by_run)
        base_cost = cost_for_agent(agent_runs)
        successes = sum(
            1
            for r in agent_runs
            if (eval_by_run.get(str(r.get("id", ""))) or {}).get("acceptance_pass") in (1, True)
        )
        cost_by_agent[agent] = CostSummary(
            total_known_cost_usd=base_cost.total_known_cost_usd,
            success_count=successes,
            cost_per_success=(base_cost.total_known_cost_usd / successes if successes else None),
            coverage_known=base_cost.coverage_known,
            coverage_total=base_cost.coverage_total,
        )
        gates[agent] = {
            "acceptance_pass": successes,
            "eligible": by_agent[agent].eligible_evaluations,
        }
    paired: PairedSummary | None = None
    if len(agents) == 2:
        paired = paired_summary(runs, eval_by_run, agents[0], agents[1])
    return ScoreReport(
        by_agent=by_agent,
        paired=paired,
        runtime_by_agent=runtime_by_agent,
        cost_by_agent=cost_by_agent,
        quality_gates=gates,
    )
