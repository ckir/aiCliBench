"""SQLite persistence (§13). FK enforced, transactions, versioned schema."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ai_benchmark.provenance import _MIGRATIONS
from ai_core.errors import ConfigurationError

SCHEMA_VERSION = 2

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    status TEXT NOT NULL,
    suite TEXT NOT NULL,
    task_ids_json TEXT NOT NULL,
    agent_names_json TEXT NOT NULL,
    repeat_count INTEGER NOT NULL,
    random_seed INTEGER NOT NULL,
    resolved_config_json TEXT NOT NULL,
    host_info_json TEXT NOT NULL,
    tool_versions_json TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    provenance_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    repetition INTEGER NOT NULL,
    pair_key TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    status TEXT NOT NULL,
    requested_model TEXT,
    reported_model TEXT,
    cli_version TEXT,
    starting_commit TEXT NOT NULL DEFAULT '',
    instruction_sha256 TEXT NOT NULL DEFAULT '',
    environment_digest TEXT NOT NULL DEFAULT '',
    evaluator_digest TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL DEFAULT '',
    ended_at TEXT NOT NULL DEFAULT '',
    elapsed_seconds REAL NOT NULL DEFAULT 0,
    exit_code INTEGER,
    error_category TEXT,
    error_message TEXT,
    usage_json TEXT NOT NULL DEFAULT '{}',
    artifact_dir TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    acceptance_pass INTEGER,
    exit_code INTEGER,
    duration_seconds REAL NOT NULL DEFAULT 0,
    tests_passed INTEGER,
    tests_failed INTEGER,
    tests_skipped INTEGER,
    build_pass INTEGER,
    lint_pass INTEGER,
    typecheck_pass INTEGER,
    regression_pass INTEGER,
    output_json TEXT NOT NULL DEFAULT '{}',
    evaluator_version TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    sha256 TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    redacted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT ''
);
"""


def connect(path: Path) -> sqlite3.Connection:
    """Open the database, enforce FK, and apply migrations."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)

    # Check current schema version
    row = conn.execute(
        "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
    ).fetchone()
    current_version = row[0] if row else 0

    # Apply migrations
    for version in range(current_version + 1, SCHEMA_VERSION + 1):
        if version in _MIGRATIONS:
            for stmt in _MIGRATIONS[version]:
                try:
                    conn.execute(stmt)
                except sqlite3.OperationalError as e:
                    # Column might already exist
                    if "duplicate column" not in str(e).lower():
                        raise
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
                (version,),
            )

    if current_version > SCHEMA_VERSION:
        raise ConfigurationError(f"unsupported schema version: {current_version}")

    return conn


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


_RUN_COLUMNS = frozenset(
    {
        "id",
        "experiment_id",
        "task_id",
        "agent_name",
        "repetition",
        "pair_key",
        "order_index",
        "status",
        "requested_model",
        "reported_model",
        "cli_version",
        "starting_commit",
        "instruction_sha256",
        "environment_digest",
        "evaluator_digest",
        "started_at",
        "ended_at",
        "elapsed_seconds",
        "exit_code",
        "error_category",
        "error_message",
        "usage_json",
        "artifact_dir",
    }
)


def insert_experiment(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    # Provide default for provenance_json if not present
    record.setdefault("provenance_json", "{}")
    conn.execute(
        """
        INSERT INTO experiments
        (id, created_at, started_at, ended_at, status, suite, task_ids_json,
         agent_names_json, repeat_count, random_seed, resolved_config_json,
         host_info_json, tool_versions_json, notes, provenance_json)
        VALUES (:id, :created_at, :started_at, :ended_at, :status, :suite,
         :task_ids_json, :agent_names_json, :repeat_count, :random_seed,
         :resolved_config_json, :host_info_json, :tool_versions_json, :notes, :provenance_json)
        """,
        record,
    )


def update_experiment_status(
    conn: sqlite3.Connection, experiment_id: str, *, status: str, ended_at: str | None = None
) -> None:
    if ended_at is None:
        conn.execute("UPDATE experiments SET status=? WHERE id=?", (status, experiment_id))
    else:
        conn.execute(
            "UPDATE experiments SET status=?, ended_at=? WHERE id=?",
            (status, ended_at, experiment_id),
        )


def update_experiment_provenance(
    conn: sqlite3.Connection, experiment_id: str, provenance_json: str
) -> None:
    """Update the provenance_json column for an experiment."""
    conn.execute(
        "UPDATE experiments SET provenance_json = ? WHERE id = ?",
        (provenance_json, experiment_id),
    )


def insert_run(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO runs
        (id, experiment_id, task_id, agent_name, repetition, pair_key, order_index,
         status, requested_model, reported_model, cli_version, starting_commit,
         instruction_sha256, environment_digest, evaluator_digest, started_at, ended_at,
         elapsed_seconds, exit_code, error_category, error_message, usage_json, artifact_dir)
        VALUES (:id, :experiment_id, :task_id, :agent_name, :repetition, :pair_key,
         :order_index, :status, :requested_model, :reported_model, :cli_version,
         :starting_commit, :instruction_sha256, :environment_digest, :evaluator_digest,
         :started_at, :ended_at, :elapsed_seconds, :exit_code, :error_category,
         :error_message, :usage_json, :artifact_dir)
        """,
        record,
    )


def update_run(conn: sqlite3.Connection, run_id: str, fields: dict[str, Any]) -> None:
    unknown = set(fields) - _RUN_COLUMNS
    if unknown:
        raise ConfigurationError(f"unknown run columns: {sorted(unknown)}")
    sets = ", ".join(f"{key}=?" for key in fields)
    conn.execute(
        f"UPDATE runs SET {sets} WHERE id=?",  # noqa: S608 - column names validated
        (*fields.values(), run_id),
    )


def insert_evaluation(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO evaluations
        (id, run_id, status, acceptance_pass, exit_code, duration_seconds,
         tests_passed, tests_failed, tests_skipped, build_pass, lint_pass,
         typecheck_pass, regression_pass, output_json, evaluator_version)
        VALUES (:id, :run_id, :status, :acceptance_pass, :exit_code, :duration_seconds,
         :tests_passed, :tests_failed, :tests_skipped, :build_pass, :lint_pass,
         :typecheck_pass, :regression_pass, :output_json, :evaluator_version)
        """,
        record,
    )


def insert_artifact(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO artifacts
        (id, run_id, kind, relative_path, sha256, size_bytes, redacted, created_at)
        VALUES (:id, :run_id, :kind, :relative_path, :sha256, :size_bytes, :redacted, :created_at)
        """,
        record,
    )


def list_experiments(conn: sqlite3.Connection, *, limit: int = 20) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return list(
        conn.execute("SELECT * FROM experiments ORDER BY created_at DESC LIMIT ?", (limit,))
    )


def get_experiment(conn: sqlite3.Connection, experiment_id: str) -> dict[str, Any] | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM experiments WHERE id=?", (experiment_id,)).fetchone()
    return dict(row) if row else None


def runs_for_experiment(conn: sqlite3.Connection, experiment_id: str) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM runs WHERE experiment_id=? ORDER BY task_id, repetition, order_index",
        (experiment_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def evaluation_for_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM evaluations WHERE run_id=?", (run_id,)).fetchone()
    return dict(row) if row else None


def latest_experiment_id(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT id FROM experiments ORDER BY created_at DESC LIMIT 1").fetchone()
    return row[0] if row else None