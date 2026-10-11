"""Static HTML reporting (§15). Local data only; all text escaped."""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, select_autoescape

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<style>
body { font-family: sans-serif; margin: 2rem; }
table { border-collapse: collapse; margin: 1rem 0; }
th, td { border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }
.warning { background: #fff3cd; border: 1px solid #ffc107; padding: 0.6rem; }
.warning { margin: 1rem 0; }
code { background: #f6f6f6; padding: 0 0.2rem; }
</style>
</head>
<body>
<h1>{{ title }}</h1>

<h2>1. Experiment metadata and resolved configuration</h2>
<p>Experiment <code>{{ experiment.id }}</code> · suite
<code>{{ experiment.suite }}</code> · status
<code>{{ experiment.status }}</code> · seed
<code>{{ experiment.random_seed }}</code></p>
<pre>{{ resolved_config }}</pre>

<h2>2. Agent versions and model identity confidence</h2>
<table><tr><th>Agent</th><th>Version</th></tr>
{% for agent, version in tool_versions.items() %}
<tr><td>{{ agent }}</td><td>{{ version }}</td></tr>
{% endfor %}
</table>
{% if model_unknown %}
<div class="warning">Model identity unknown for one or more agents;
this is a CLI-configuration comparison, not a controlled
model comparison.</div>
{% endif %}

<h2>3. Overall pass rate (numerators and denominators)</h2>
<table><tr><th>Agent</th><th>Passes</th><th>Eligible</th><th>Pass rate</th></tr>
{% for agent, row in correctness.items() %}
<tr><td>{{ agent }}</td><td>{{ row.passes }}</td>
<td>{{ row.eligible }}</td><td>{{ row.rate }}</td></tr>
{% endfor %}
</table>

<h2>4. Paired task outcomes</h2>
<p>A wins {{ paired.a_wins }}, B wins {{ paired.b_wins }},
both pass {{ paired.both_pass }}, neither {{ paired.neither_pass }},
invalid {{ paired.invalid }} (total {{ paired.total_pairs }}).</p>

<h2>5. Per-category pass rates</h2>
<table><tr><th>Agent</th><th>Passes</th><th>Eligible</th></tr>
{% for agent, row in correctness.items() %}
<tr><td>{{ agent }}</td><td>{{ row.passes }}</td>
<td>{{ row.eligible }}</td></tr>
{% endfor %}
</table>

<h2>6. Median successful runtime and IQR</h2>
<table>
<tr><th>Agent</th><th>N success</th><th>Median (s)</th><th>IQR (s)</th>
<th>Timeouts</th></tr>
{% for agent, row in runtime.items() %}
<tr><td>{{ agent }}</td><td>{{ row.n }}</td>
<td>{{ row.median }}</td><td>{{ row.iqr }}</td>
<td>{{ row.timeouts }}</td></tr>
{% endfor %}
</table>

<h2>7. Timeout/error rates</h2>
<table>
<tr><th>Agent</th><th>Timeout</th><th>Agent error</th>
<th>Setup error</th><th>Eval error</th></tr>
{% for agent, row in errors.items() %}
<tr><td>{{ agent }}</td><td>{{ row.timeout }}</td>
<td>{{ row.agent_error }}</td><td>{{ row.setup }}</td>
<td>{{ row.eval_error }}</td></tr>
{% endfor %}
</table>

<h2>8. Cost/usage with data-coverage warnings</h2>
<table>
<tr><th>Agent</th><th>Known cost (USD)</th><th>Cost/success</th>
<th>Coverage</th></tr>
{% for agent, row in cost.items() %}
<tr><td>{{ agent }}</td><td>{{ row.total }}</td>
<td>{{ row.per_success }}</td><td>{{ row.coverage }}</td></tr>
{% endfor %}
</table>
{% if cost_warning %}<div class="warning">{{ cost_warning }}</div>{% endif %}

<h2>9. Quality-gate results</h2>
<table><tr><th>Agent</th><th>Acceptance</th><th>Build</th><th>Lint</th><th>Typecheck</th></tr>
{% for agent, row in quality_gates.items() %}
<tr>
  <td>{{ agent }}</td>
  <td>{{ row.acceptance_pass }}/{{ row.eligible }}</td>
  <td>{% if row.build_total %}{{ row.build_pass }}/{{ row.build_total }}{% else %}n/a{% endif %}</td>
  <td>{% if row.lint_total %}{{ row.lint_pass }}/{{ row.lint_total }}{% else %}n/a{% endif %}</td>
  <td>{% if row.typecheck_total %}{{ row.typecheck_pass }}/{{ row.typecheck_total }}{% else %}n/a{% endif %}</td>
</tr>
{% endfor %}
</table>

<h2>10. Per-task comparison</h2>
<table>
<tr><th>Task</th><th>Rep</th><th>Agent</th><th>Run</th><th>Eval</th>
<th>Seconds</th></tr>
{% for row in per_task %}
<tr><td>{{ row.task_id }}</td><td>{{ row.repetition }}</td>
<td>{{ row.agent }}</td><td>{{ row.run_status }}</td>
<td>{{ row.eval_status }}</td><td>{{ row.seconds }}</td></tr>
{% endfor %}
</table>

<h2>11. Failures grouped by category</h2>
<table><tr><th>Category</th><th>Count</th></tr>
{% for category, count in failures.items() %}
<tr><td>{{ category }}</td><td>{{ count }}</td></tr>
{% endfor %}
</table>

<h2>12. Warnings</h2>
{% if warnings %}
{% for warning in warnings %}
<div class="warning">{{ warning }}</div>
{% endfor %}
{% else %}<p>No warnings.</p>{% endif %}

</body>
</html>
"""


def _fmt(value: object) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def render_report(
    *,
    title: str,
    experiment: dict[str, Any],
    runs: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
    score: Any,
    tool_versions: dict[str, Any],
    warnings: list[str],
) -> str:
    """Render the 12-section report with autoescaping (§15)."""
    env = Environment(autoescape=select_autoescape(["html"]))
    template = env.from_string(_TEMPLATE)
    eval_by_run = {str(e.get("run_id")): e for e in evaluations}

    correctness: dict[str, dict[str, str]] = {}
    errors: dict[str, dict[str, str]] = {}
    runtime: dict[str, dict[str, str]] = {}
    cost: dict[str, dict[str, str]] = {}
    for agent, summary in score.by_agent.items():
        rate = f"{summary.pass_rate:.2%}" if summary.pass_rate is not None else "n/a"
        correctness[agent] = {
            "passes": str(summary.acceptance_passes),
            "eligible": str(summary.eligible_evaluations),
            "rate": rate,
        }
        errors[agent] = {
            "timeout": f"{summary.timeout_rate:.1%}",
            "agent_error": f"{summary.agent_error_rate:.1%}",
            "setup": f"{summary.setup_error_rate:.1%}",
            "eval_error": f"{summary.evaluation_error_rate:.1%}",
        }
    for agent, summary in score.runtime_by_agent.items():
        runtime[agent] = {
            "n": str(summary.successful_count),
            "median": _fmt(summary.median_success_seconds),
            "iqr": _fmt(summary.iqr_success_seconds),
            "timeouts": str(summary.timeout_count),
        }
    cost_warning: str | None = None
    for agent, summary in score.cost_by_agent.items():
        per_success = (
            f"{summary.cost_per_success:.4f}"
            if summary.cost_per_success is not None
            else "not available"
        )
        coverage = f"{summary.coverage_known}/{summary.coverage_total} known"
        cost[agent] = {
            "total": f"{summary.total_known_cost_usd:.4f}",
            "per_success": per_success,
            "coverage": coverage,
        }
        if summary.coverage_known < summary.coverage_total:
            cost_warning = (
                "Cost data incomplete: showing known-cost subset only. "
                "Subscription plans without per-run telemetry display as not available."
            )

    if score.paired is not None:
        paired = {
            "a_wins": score.paired.a_wins,
            "b_wins": score.paired.b_wins,
            "both_pass": score.paired.both_pass,
            "neither_pass": score.paired.neither_pass,
            "invalid": score.paired.invalid,
            "total_pairs": score.paired.total_pairs,
        }
    else:
        paired = {
            "a_wins": 0,
            "b_wins": 0,
            "both_pass": 0,
            "neither_pass": 0,
            "invalid": 0,
            "total_pairs": 0,
        }

    per_task = [
        {
            "task_id": run.get("task_id", ""),
            "repetition": run.get("repetition", ""),
            "agent": run.get("agent_name", ""),
            "run_status": run.get("status", ""),
            "eval_status": (eval_by_run.get(str(run.get("id", ""))) or {}).get("status", ""),
            "seconds": run.get("elapsed_seconds", ""),
        }
        for run in sorted(runs, key=lambda r: (str(r.get("task_id")), str(r.get("id"))))
    ]
    failures: dict[str, int] = {}
    for run in runs:
        category = str(run.get("error_category") or run.get("status", "unknown"))
        failures[category] = failures.get(category, 0) + 1

    model_unknown = any(
        not run.get("reported_model") for run in runs if run.get("status") == "completed"
    )

    import json as _json

    return template.render(
        title=title,
        experiment=experiment,
        resolved_config=_json.dumps(experiment.get("resolved_config_json", {}), indent=2)[:8000],
        tool_versions={k: _fmt(v) for k, v in tool_versions.items()},
        model_unknown=model_unknown,
        correctness=correctness,
        quality_gates=score.quality_gates,
        paired=paired,
        runtime=runtime,
        errors=errors,
        cost=cost,
        cost_warning=cost_warning,
        per_task=per_task,
        failures=failures,
        warnings=warnings,
    )
