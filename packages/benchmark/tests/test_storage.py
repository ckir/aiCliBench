import json
import sqlite3
from pathlib import Path

import pytest

from ai_benchmark.storage import (
    connect,
    evaluation_for_run,
    get_experiment,
    insert_artifact,
    insert_evaluation,
    insert_experiment,
    insert_run,
    latest_experiment_id,
    list_experiments,
    runs_for_experiment,
    update_experiment_status,
    update_run,
)


def _exp(exp_id: str = "exp_1") -> dict:
    return {
        "id": exp_id,
        "created_at": "2026-10-10T00:00:00Z",
        "started_at": "2026-10-10T00:00:00Z",
        "ended_at": None,
        "status": "running",
        "suite": "pilot",
        "task_ids_json": json.dumps(["example-task"]),
        "agent_names_json": json.dumps(["claude"]),
        "repeat_count": 1,
        "random_seed": 42,
        "resolved_config_json": "{}",
        "host_info_json": "{}",
        "tool_versions_json": "{}",
        "notes": "",
    }


def test_schema_and_crud(tmp_path: Path):
    conn = connect(tmp_path / "codebench.sqlite3")
    insert_experiment(conn, _exp())
    conn.commit()
    exp_row = get_experiment(conn, "exp_1")
    assert exp_row is not None
    assert exp_row["suite"] == "pilot"

    insert_run(
        conn,
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
            "instruction_sha256": "abc",
            "environment_digest": "",
            "evaluator_digest": "",
            "started_at": "2026-10-10T00:00:00Z",
            "ended_at": "2026-10-10T00:01:00Z",
            "elapsed_seconds": 60.0,
            "exit_code": 0,
            "error_category": None,
            "error_message": None,
            "usage_json": "{}",
            "artifact_dir": "runs/exp_1/run_1",
        },
    )
    conn.commit()
    runs = runs_for_experiment(conn, "exp_1")
    assert len(runs) == 1

    update_run(conn, "run_1", {"status": "timeout"})
    conn.commit()
    assert runs_for_experiment(conn, "exp_1")[0]["status"] == "timeout"

    insert_evaluation(
        conn,
        {
            "id": "eval_1",
            "run_id": "run_1",
            "status": "pass",
            "acceptance_pass": 1,
            "exit_code": 0,
            "duration_seconds": 5.0,
            "tests_passed": 3,
            "tests_failed": 0,
            "tests_skipped": 0,
            "build_pass": None,
            "lint_pass": None,
            "typecheck_pass": None,
            "regression_pass": None,
            "output_json": "{}",
            "evaluator_version": "v1",
        },
    )
    insert_artifact(
        conn,
        {
            "id": "art_1",
            "run_id": "run_1",
            "kind": "stdout",
            "relative_path": "stdout.log",
            "sha256": "abc",
            "size_bytes": 3,
            "redacted": 0,
            "created_at": "2026-10-10T00:00:00Z",
        },
    )
    conn.commit()
    eval_row = evaluation_for_run(conn, "run_1")
    assert eval_row is not None
    assert eval_row["status"] == "pass"
    assert latest_experiment_id(conn) == "exp_1"
    assert len(list_experiments(conn)) == 1

    update_experiment_status(conn, "exp_1", status="completed", ended_at="2026-10-10T01:00:00Z")
    conn.commit()
    exp_row = get_experiment(conn, "exp_1")
    assert exp_row is not None
    assert exp_row["status"] == "completed"
    conn.close()


def test_foreign_keys_enforced(tmp_path: Path):
    conn = connect(tmp_path / "db.sqlite3")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO runs (id, experiment_id, task_id, agent_name, repetition,"
            " pair_key, order_index, status) VALUES ('r','missing','t','a',1,'k',0,'completed')"
        )
    conn.close()


def test_transactions_rollback(tmp_path: Path):
    conn = connect(tmp_path / "db2.sqlite3")
    insert_experiment(conn, _exp("exp_tx"))
    conn.commit()
    try:
        with conn:
            conn.execute("INSERT INTO runs (id, experiment_id, task_id) VALUES ('x','exp_tx','t')")
    except sqlite3.IntegrityError:
        pass
    # Experiment insert survived; bad run did not.
    assert get_experiment(conn, "exp_tx") is not None
    assert runs_for_experiment(conn, "exp_tx") == []
    conn.close()
