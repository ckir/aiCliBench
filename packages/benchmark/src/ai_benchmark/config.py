"""Benchmark configuration loading (§6). Secrets never live in config or SQLite."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from ai_core.errors import ConfigurationError
from ai_schemas import BenchmarkConfig


def load_config_file(path: Path) -> BenchmarkConfig:
    """Load and validate a `benchmark.toml` file.

    Raises:
        ConfigurationError: when the file is missing, unparsable, or invalid.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigurationError(f"cannot read config {path}: {exc}") from exc
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ConfigurationError(f"invalid TOML in {path}: {exc}") from exc
    try:
        return BenchmarkConfig.model_validate(data)
    except Exception as exc:
        raise ConfigurationError(f"invalid benchmark config in {path}: {exc}") from exc


def default_config() -> BenchmarkConfig:
    """Return documented defaults (§6 example)."""
    return BenchmarkConfig()


def apply_overrides(config: BenchmarkConfig, overrides: dict[str, Any]) -> BenchmarkConfig:
    """Apply explicit CLI-flag overrides to a validated config.

    Supported keys (dot or nested): e.g. ``{"execution.random_seed": 1}``
    or ``{"execution": {"random_seed": 1}}``. Unknown keys raise.
    """
    data = config.model_dump()
    for key, value in overrides.items():
        if "." in key:
            section, _, field = key.partition(".")
            if section not in data or not isinstance(data[section], dict):
                raise ConfigurationError(f"unknown config override: {key!r}")
            if field not in data[section]:
                raise ConfigurationError(f"unknown config override: {key!r}")
            data[section][field] = value
        else:
            # Allow top-level section replacement only when valid.
            if key not in data:
                raise ConfigurationError(f"unknown config override: {key!r}")
            data[key] = value
    try:
        return BenchmarkConfig.model_validate(data)
    except Exception as exc:
        raise ConfigurationError(f"invalid config override: {exc}") from exc


def resolve_config(path: Path | None, overrides: dict[str, Any] | None = None) -> BenchmarkConfig:
    """Load config from *path* (or defaults) and apply *overrides*."""
    config = load_config_file(path) if path is not None else default_config()
    if overrides:
        config = apply_overrides(config, overrides)
    return config


def config_snapshot(config: BenchmarkConfig) -> dict[str, Any]:
    """Return a JSON-compatible snapshot for experiment metadata (§10)."""
    return config.model_dump(mode="json")
