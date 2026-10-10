"""Deterministic JSON/CSV export (§15). Includes schema/version metadata."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

EXPORT_SCHEMA_VERSION = 1


def export_json(
    *,
    experiment: dict[str, Any],
    runs: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
) -> str:
    """Return deterministic pretty JSON (sorted keys, stable order)."""
    payload = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "experiment": experiment,
        "runs": sorted(runs, key=lambda r: str(r.get("id", ""))),
        "evaluations": sorted(evaluations, key=lambda e: str(e.get("id", ""))),
    }
    return json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"


def flatten_run(run: dict[str, Any], evaluation: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten one run + evaluation to a CSV-friendly row."""
    evaluation = evaluation or {}
    usage: dict[str, Any] = {}
    try:
        parsed = json.loads(run.get("usage_json", "{}") or "{}")
        if isinstance(parsed, dict):
            usage = parsed
    except (json.JSONDecodeError, ValueError):
        usage = {}
    return {
        "run_id": run.get("id", ""),
        "experiment_id": run.get("experiment_id", ""),
        "task_id": run.get("task_id", ""),
        "agent_name": run.get("agent_name", ""),
        "repetition": run.get("repetition", ""),
        "pair_key": run.get("pair_key", ""),
        "order_index": run.get("order_index", ""),
        "run_status": run.get("status", ""),
        "requested_model": run.get("requested_model", ""),
        "reported_model": run.get("reported_model", ""),
        "cli_version": run.get("cli_version", ""),
        "starting_commit": run.get("starting_commit", ""),
        "elapsed_seconds": run.get("elapsed_seconds", ""),
        "exit_code": run.get("exit_code", ""),
        "error_category": run.get("error_category", ""),
        "eval_status": evaluation.get("status", ""),
        "acceptance_pass": evaluation.get("acceptance_pass", ""),
        "eval_exit_code": evaluation.get("exit_code", ""),
        "tests_passed": evaluation.get("tests_passed", ""),
        "tests_failed": evaluation.get("tests_failed", ""),
        "cost_usd": usage.get("cost_usd", ""),
        "input_tokens": usage.get("input_tokens", ""),
        "output_tokens": usage.get("output_tokens", ""),
    }


_CSV_FIELDS = [
    "run_id",
    "experiment_id",
    "task_id",
    "agent_name",
    "repetition",
    "pair_key",
    "order_index",
    "run_status",
    "requested_model",
    "reported_model",
    "cli_version",
    "starting_commit",
    "elapsed_seconds",
    "exit_code",
    "error_category",
    "eval_status",
    "acceptance_pass",
    "eval_exit_code",
    "tests_passed",
    "tests_failed",
    "cost_usd",
    "input_tokens",
    "output_tokens",
]


def export_csv(
    *,
    runs: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
) -> str:
    """Return deterministic CSV (sorted by run id, fixed columns)."""
    eval_by_run = {str(e.get("run_id")): e for e in evaluations}
    ordered = sorted(runs, key=lambda r: str(r.get("id", "")))
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for run in ordered:
        writer.writerow(flatten_run(run, eval_by_run.get(str(run.get("id", "")))))
    return buffer.getvalue()
