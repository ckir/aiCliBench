"""Configuration deep merge and variable expansion."""

import copy
from typing import Any


def deep_merge(base: dict, override: dict, list_strategy: str = "replace") -> dict:
    # Incomplete stub
    if list_strategy not in ("replace", "append"):
        raise ValueError(f"Invalid strategy: {list_strategy}")
    res = copy.deepcopy(base)
    res.update(override)
    return res


def expand_env_vars(data: Any, env: dict[str, str]) -> Any:
    # Incomplete stub
    return data
