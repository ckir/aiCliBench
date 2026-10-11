"""Hidden acceptance tests for config_merger."""

import pytest
from config_merger import deep_merge, expand_env_vars  # ty: ignore[unresolved-import]


def test_deep_dict_merge():
    base = {"db": {"host": "localhost", "port": 5432}, "logging": {"level": "INFO"}}
    override = {"db": {"port": 5433, "user": "admin"}}
    merged = deep_merge(base, override)
    assert merged == {
        "db": {"host": "localhost", "port": 5433, "user": "admin"},
        "logging": {"level": "INFO"},
    }
    # Ensure immutability
    assert base["db"]["port"] == 5432


def test_list_merge_strategies():
    base = {"tags": ["a", "b"]}
    override = {"tags": ["c"]}
    assert deep_merge(base, override, "replace") == {"tags": ["c"]}
    assert deep_merge(base, override, "append") == {"tags": ["a", "b", "c"]}


def test_env_var_expansion():
    cfg = {
        "host": "${APP_HOST}",
        "port": "${APP_PORT:-8080}",
        "nested": ["${UNKNOWN:-fallback}"],
    }
    env = {"APP_HOST": "0.0.0.0"}
    expanded = expand_env_vars(cfg, env)
    assert expanded == {
        "host": "0.0.0.0",
        "port": "8080",
        "nested": ["fallback"],
    }

    with pytest.raises(KeyError):
        expand_env_vars({"val": "${MISSING}"}, {})
