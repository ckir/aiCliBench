from ai_benchmark.scoring import (
    correctness_for_agent,
    cost_for_agent,
    paired_summary,
    runtime_for_agent,
    score_experiment,
)


def _run(run_id: str, agent: str, status: str, elapsed: float = 10.0, usage: str = "{}") -> dict:
    return {
        "id": run_id,
        "agent_name": agent,
        "status": status,
        "pair_key": "t:1",
        "elapsed_seconds": elapsed,
        "usage_json": usage,
    }


def test_correctness_denominators():
    runs = [
        _run("r1", "claude", "completed"),
        _run("r2", "claude", "timeout"),
        _run("r3", "claude", "completed"),
    ]
    evals = {
        "r1": {"status": "pass", "acceptance_pass": 1},
        "r3": {"status": "evaluation_error", "acceptance_pass": None},
    }
    summary = correctness_for_agent(runs, evals)
    # r3 eval error excluded from denominator; r2 timeout not eligible either.
    assert summary.eligible_evaluations == 1
    assert summary.acceptance_passes == 1
    assert summary.pass_rate == 1.0
    assert summary.evaluation_error_rate == 1 / 3


def test_paired_wins_and_ties():
    runs = [
        {**_run("a1", "claude", "completed"), "pair_key": "t:1"},
        {**_run("b1", "antigravity", "completed"), "pair_key": "t:1"},
        {**_run("a2", "claude", "completed"), "pair_key": "t:2"},
        {**_run("b2", "antigravity", "completed"), "pair_key": "t:2"},
    ]
    evals = {
        "a1": {"status": "pass", "acceptance_pass": 1},
        "b1": {"status": "fail", "acceptance_pass": 0},
        "a2": {"status": "pass", "acceptance_pass": 1},
        "b2": {"status": "pass", "acceptance_pass": 1},
    }
    paired = paired_summary(runs, evals, "antigravity", "claude")
    assert paired.a_wins + paired.b_wins + paired.both_pass == 2
    assert paired.both_pass == 1
    assert paired.total_pairs == 2


def test_runtime_median_iqr_success_only():
    runs = [
        _run("r1", "claude", "completed", elapsed=10.0),
        _run("r2", "claude", "completed", elapsed=20.0),
        _run("r3", "claude", "timeout", elapsed=900.0),
        _run("r4", "claude", "completed", elapsed=30.0),
    ]
    evals = {
        "r1": {"status": "pass", "acceptance_pass": 1},
        "r2": {"status": "fail", "acceptance_pass": 0},
        "r4": {"status": "pass", "acceptance_pass": 1},
    }
    runtime = runtime_for_agent(runs, evals)
    # Only r1 and r4 are successful; timeout excluded from median.
    assert runtime.successful_count == 2
    assert runtime.median_success_seconds == 20.0
    assert runtime.timeout_count == 1


def test_cost_coverage_never_invented():
    runs = [
        _run("r1", "claude", "completed", usage='{"cost_usd": 0.5}'),
        _run("r2", "claude", "completed", usage="{}"),
    ]
    cost = cost_for_agent(runs)
    assert cost.total_known_cost_usd == 0.5
    assert cost.coverage_known == 1
    assert cost.coverage_total == 2


def test_score_experiment_end_to_end():
    runs = [_run("r1", "claude", "completed"), _run("r2", "antigravity", "completed")]
    evals = [
        {"run_id": "r1", "status": "pass", "acceptance_pass": 1},
        {"run_id": "r2", "status": "fail", "acceptance_pass": 0},
    ]
    report = score_experiment(runs, evals)
    assert report.by_agent["claude"].pass_rate == 1.0
    assert report.by_agent["antigravity"].pass_rate == 0.0
    assert report.paired is not None
