"""Provenance manifest, environment digest, and image cache (§15)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_core.errors import ConfigurationError


def environment_digest(task_dir: Path, dockerfile_rel: str) -> str:
    """Compute SHA256 of Dockerfile and source files for reproducibility.

    Args:
        task_dir: Task directory containing source/ and Dockerfile
        dockerfile_rel: Relative path to Dockerfile from task_dir

    Returns:
        Hex digest string
    """
    hasher = hashlib.sha256()
    dockerfile_path = task_dir / dockerfile_rel
    if dockerfile_path.is_file():
        hasher.update(b"dockerfile\0")
        hasher.update(dockerfile_path.read_bytes())
    else:
        hasher.update(b"dockerfile\0")
        hasher.update(b"missing")

    source_dir = task_dir / "source"
    if source_dir.is_dir():
        for src_path in sorted(source_dir.rglob("*")):
            if not src_path.is_file():
                continue
            rel = src_path.relative_to(source_dir)
            if any(part in ("__pycache__", ".pytest_cache") for part in rel.parts):
                continue
            if rel.suffix == ".pyc":
                continue
            hasher.update(rel.as_posix().encode())
            hasher.update(b"\0")
            hasher.update(src_path.read_bytes())

    return hasher.hexdigest()


@dataclass(frozen=True, slots=True)
class ImageInfo:
    image_id: str
    size_bytes: int


def inspect_image(tag: str) -> ImageInfo | None:
    """Inspect a Docker image for ID and size.

    Args:
        tag: Image tag to inspect

    Returns:
        ImageInfo if successful, None otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}} {{.Size}}", tag],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        parts = result.stdout.strip().split()
        if len(parts) != 2:
            return None
        return ImageInfo(image_id=parts[0], size_bytes=int(parts[1]))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


class ImageCache:
    """Cache for Docker image builds to avoid redundant builds."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(".codebench/images.json")
        self._data: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def load(self) -> dict[str, dict[str, Any]]:
        if not self._loaded:
            if self.path.is_file():
                try:
                    self._data = json.loads(self.path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, ValueError):
                    self._data = {}
            self._loaded = True
        return self._data

    def get(self, task_id: str) -> dict[str, Any] | None:
        return self.load().get(task_id)

    def put(
        self,
        task_id: str,
        *,
        tag: str,
        environment_digest: str,
        image_id: str,
        size_bytes: int,
    ) -> None:
        data = self.load()
        data[task_id] = {
            "tag": tag,
            "environment_digest": environment_digest,
            "image_id": image_id,
            "size_bytes": size_bytes,
            "built_at": datetime.now(UTC).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
        tmp.replace(self.path)


def build_manifest(
    *,
    prompt_wrapper_version: str,
    docker: str | None,
    agents: dict[str, dict[str, Any]],
    tasks: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a provenance manifest for an experiment.

    Args:
        prompt_wrapper_version: Version of the prompt wrapper used
        docker: Docker version string or None
        agents: Agent name -> version/capability info
        tasks: Task ID -> {commit, environment_digest, image_id}

    Returns:
        Manifest dictionary
    """
    return {
        "schema_version": 2,
        "created_at": datetime.now(UTC).isoformat(),
        "prompt_wrapper_version": prompt_wrapper_version,
        "docker_version": docker,
        "agents": agents,
        "tasks": tasks,
    }


_MIGRATIONS: dict[int, list[str]] = {
    2: ["ALTER TABLE experiments ADD COLUMN provenance_json TEXT NOT NULL DEFAULT '{}'"],
}


def connect_with_migrations(path: Path) -> "sqlite3.Connection":
    """Open the database, enforce FK, and apply migrations."""
    import sqlite3

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")

    # Check current schema version
    row = conn.execute(
        "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
    ).fetchone()
    current_version = row[0] if row else 0

    # Apply migrations
    SCHEMA_VERSION = 2
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


def update_experiment_provenance(
    conn: "sqlite3.Connection", experiment_id: str, provenance_json: str
) -> None:
    """Update the provenance_json column for an experiment."""
    conn.execute(
        "UPDATE experiments SET provenance_json = ? WHERE id = ?",
        (provenance_json, experiment_id),
    )