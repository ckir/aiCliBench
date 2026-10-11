import json

from ai_benchmark.export import export_csv, export_json, flatten_run
from ai_benchmark.reporting import render_report
from ai_benchmark.scoring import score_experiment


def _sample():
    runs = [
        {
            "id": "run_1",
            "experiment_id": "exp_1",
            "task_id": "example-task",
            "agent_name": "claude",
            "repetition": 1,
            "pair_key": "example-task:1",
            "order_index": 0,
            "status": "completed",
            "requested_model": None,
            "reported_model": None,
            "cli_version": "1.0",
            "starting_commit": "0" * 40,
            "elapsed_seconds": 12.0,
            "exit_code": 0,
            "error_category": None,
            "usage_json": "{}",
        }
    ]
    evals = [{"id": "eval_1", "run_id": "run_1", "status": "pass", "acceptance_pass": 1}]
    exp = {
        "id": "exp_1",
        "suite": "pilot",
        "status": "completed",
        "random_seed": 1,
        "resolved_config_json": "{}",
    }
    return exp, runs, evals


def test_export_json_deterministic():
    exp, runs, evals = _sample()
    first = export_json(experiment=exp, runs=runs, evaluations=evals)
    second = export_json(experiment=exp, runs=runs, evaluations=evals)
    assert first == second
    payload = json.loads(first)
    assert payload["schema_version"] == 1
    assert payload["runs"][0]["id"] == "run_1"


def test_export_csv_columns_and_order():
    _, runs, evals = _sample()
    one = export_csv(runs=runs, evaluations=evals)
    two = export_csv(runs=list(reversed(runs)), evaluations=evals)
    assert one == two
    assert one.splitlines()[0].startswith("run_id,experiment_id,task_id")
    assert "run_1" in one


def test_html_escapes_injection():
    exp, runs, evals = _sample()
    runs[0]["task_id"] = '<script>alert("x")</script>'
    score = score_experiment(runs, evals)
    html = render_report(
        title="CodeBench <Test>",
        experiment=exp,
        runs=runs,
        evaluations=evals,
        score=score,
        tool_versions={"claude": "1.0"},
        warnings=[],
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    for section in (
        "Experiment metadata",
        "Agent versions",
        "Overall pass rate",
        "Paired task outcomes",
        "Per-category",
        "Median successful runtime",
        "Timeout/error",
        "Cost/usage",
        "Quality-gate",
        "Per-task comparison",
        "Failures grouped",
        "Warnings",
    ):
        assert section in html


def test_quality_gate_section_renders_build_pass():
    exp, runs, evals = _sample()
    evals[0]["build_pass"] = 1
    evals[0]["lint_pass"] = None
    evals[0]["typecheck_pass"] = None
    score = score_experiment(runs, evals)
    html = render_report(
        title="Test",
        experiment=exp,
        runs=runs,
        evaluations=evals,
        score=score,
        tool_versions={"claude": "1.0"},
        warnings=[],
    )
    assert "Build" in html
    assert "1/1" in html
    assert "Acceptance" in html


def test_flatten_includes_coverage_fields():
    row = flatten_run(
        {
            "id": "r",
            "experiment_id": "e",
            "task_id": "t",
            "agent_name": "claude",
            "repetition": 1,
            "pair_key": "k",
            "order_index": 0,
            "status": "completed",
            "usage_json": '{"cost_usd": 1.5}',
        },
        {"status": "pass", "acceptance_pass": 1},
    )
    assert row["cost_usd"] == 1.5
    assert row["eval_status"] == "pass"


def test_report_renders_provenance_table():
    exp, runs, evals = _sample()
    exp["provenance_json"] = json.dumps(
        {
            "prompt_wrapper_version": "v1",
            "docker_version": "27.0",
            "tasks": {
                "example-task": {
                    "commit": "a" * 40,
                    "evaluator_digest": "b" * 64,
                    "environment_digest": "c" * 64,
                    "image_id": None,
                }
            },
        }
    )
    html = render_report(
        title="t",
        experiment=exp,
        runs=runs,
        evaluations=evals,
        score=score_experiment(runs, evals),
        tool_versions={},
        warnings=[],
    )
    assert "Provenance" in html
    assert "a" * 12 in html
    assert "c" * 12 in html
