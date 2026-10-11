# Implement Deep Config Merger with Environment Variable Expansion

In `config_merger.py`, implement two utility functions:

1. `deep_merge(base: dict, override: dict, list_strategy: str = "replace") -> dict`:
   - Recursively merges `override` into `base`, returning a new dictionary without mutating inputs.
   - For dictionaries present in both, merges them recursively.
   - For non-dict scalars (strings, numbers, bools, etc.), `override` replaces `base`.
   - For lists present in both:
     - If `list_strategy == "replace"`: `override` list replaces `base` list.
     - If `list_strategy == "append"`: elements of `override` list are appended to `base` list.
     - Invalid `list_strategy` raises `ValueError`.

2. `expand_env_vars(data: Any, env: dict[str, str]) -> Any`:
   - Recursively traverses dictionaries, lists, and strings.
   - For string values containing `${VAR}` or `${VAR:-default}`:
     - Replaces `${VAR}` with `env[VAR]`. If `VAR` is not in `env`, raises `KeyError`.
     - Replaces `${VAR:-default}` with `env[VAR]` if present; otherwise with `default`.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
