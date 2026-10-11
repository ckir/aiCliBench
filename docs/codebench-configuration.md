# CodeBench configuration

Copy `config/benchmark.toml` and edit. The resolved configuration is recorded
for every experiment (`resolved_config_json`).

Key settings:

- `[data] directory`, `database`, `artifact_retention` (`all`|`minimal`).
- `[execution] default_timeout_seconds`, `global_max_timeout_seconds`,
  `parallelism` (MVP must stay `1`), `network_enabled_for_agent` (default
  `false`), CPU/memory/PIDs limits, `container_user`, `workspace_cleanup`
  (`retain`|`remove`), `random_seed`.
- `[agents.claude]` / `[agents.antigravity]`: `enabled`, `command`, `model`
  (empty = CLI default, recorded as unresolved), `timeout_seconds`,
  `output_format` (verified via `--help`; unsupported values are ignored with
  a recorded fallback).
- `[agents.custom.<name>]`: custom CLI agents. Each has:
  - `enabled` (bool, default true)
  - `command` (string, required)
  - `args` (list of strings, default `[]`; `{prompt}` placeholder substituted)
  - `output_format` ("json"|"jsonl"|"text", default "text")
  - `model` (string, default "")
  - `model_flag` (string, default "")
  - `version_args` (list of strings, default `["--version"]`)
  - `timeout_seconds` (int, default 900)

  Custom agent names must be lowercase alphanumeric with `-`/`_`, start with a
  letter, max 32 chars, not `claude` or `antigravity`.
- `[report] title`, `include_full_logs`.

CLI flags override config; overrides are logged. A task timeout exceeding
`global_max_timeout_seconds` fails validation unless an explicit override flag
is supplied and logged. Invalid values fail before any agent launches.
Credentials are never written to config or SQLite.