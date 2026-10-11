"""Configuration deep merge and variable expansion."""

import copy
import re
from typing import Any

ENV_REGEX = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def deep_merge(base: dict, override: dict, list_strategy: str = "replace") -> dict:
    if list_strategy not in ("replace", "append"):
        raise ValueError(f"Invalid strategy: {list_strategy}")
    result = copy.deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v, list_strategy=list_strategy)
        elif k in result and isinstance(result[k], list) and isinstance(v, list):
            if list_strategy == "append":
                result[k] = copy.deepcopy(result[k]) + copy.deepcopy(v)
            else:
                result[k] = copy.deepcopy(v)
        else:
            result[k] = copy.deepcopy(v)
    return result


def expand_env_vars(data: Any, env: dict[str, str]) -> Any:
    if isinstance(data, dict):
        return {k: expand_env_vars(v, env) for k, v in data.items()}
    if isinstance(data, list):
        return [expand_env_vars(item, env) for item in data]
    if isinstance(data, str):

        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            default = match.group(2)
            if var_name in env:
                return env[var_name]
            if default is not None:
                return default
            raise KeyError(f"Missing environment variable: {var_name}")

        return ENV_REGEX.sub(replacer, data)
    return data
