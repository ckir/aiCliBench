from pathlib import Path

import pytest

from ai_benchmark import config as config_module
from ai_benchmark.paths import ensure_within, safe_join
from ai_benchmark.redaction import redact_text
from ai_core.errors import ConfigurationError, ValidationError
from ai_schemas import BenchmarkConfig


def test_default_config_valid():
    cfg = config_module.default_config()
    assert cfg.execution.default_timeout_seconds == 900
    assert cfg.execution.parallelism == 1


def test_apply_overrides_and_unknown_rejected():
    cfg = config_module.default_config()
    updated = config_module.apply_overrides(cfg, {"execution.random_seed": 1})
    assert updated.execution.random_seed == 1
    with pytest.raises(ConfigurationError):
        config_module.apply_overrides(cfg, {"nope.field": 1})
    with pytest.raises(ConfigurationError):
        config_module.apply_overrides(cfg, {"execution.default_timeout_seconds": 0})


def test_load_missing_config_raises(tmp_path: Path):
    with pytest.raises(ConfigurationError):
        config_module.load_config_file(tmp_path / "missing.toml")


def test_load_invalid_toml_raises(tmp_path: Path):
    bad = tmp_path / "benchmark.toml"
    bad.write_text("not [valid toml", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        config_module.load_config_file(bad)


def test_config_snapshot_jsonable():
    snap = config_module.config_snapshot(BenchmarkConfig())
    assert snap["execution"]["parallelism"] == 1


def test_redaction_patterns():
    redacted, flag = redact_text("key sk-abcdefgh12345678 done")
    assert flag is True
    assert "sk-abcdefgh" not in redacted
    clean, flag2 = redact_text("hello world")
    assert flag2 is False
    assert clean == "hello world"


def test_safe_join_rejects_traversal(tmp_path: Path):
    assert safe_join(tmp_path, "instruction.md").name == "instruction.md"
    with pytest.raises(ValidationError):
        safe_join(tmp_path, "../evil.md")
    with pytest.raises(ValidationError):
        safe_join(tmp_path, "/abs/path")
    with pytest.raises(ValidationError):
        ensure_within(tmp_path, tmp_path.parent / "evil")
