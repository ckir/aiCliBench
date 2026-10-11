# Adding a CodeBench task

Each task is `tasks/<suite>/<task-id>/` with:

- `task.toml` (schema_version, id, title, category, suite, description,
  repository, commit full 40-char SHA, instruction_file, dockerfile,
  evaluator_command, timeouts, resource overrides, tags, environment, scoring).
- `instruction.md`: only the prompt sent to the agent. Same bytes to both
  agents; SHA-256 recorded. Must not contain hidden tests or hints.
- `environment/Dockerfile`: offline-buildable after base images are cached.
- `evaluator/run_tests.sh` + `evaluator/tests/`: trusted acceptance tests.
- `solution/README.md`: reference fix for validators (never mounted to agents).
- `solution/files/`: reference implementation overlay (copied to workspace for verification).

## Task lifecycle

### 1. Creating a task (scaffolding)

Use `codebench tasks init <task-id> --title TITLE --category CATEGORY [--suite SUITE] [--description DESC]`.

This creates:
- `task.toml` with a placeholder commit (all zeros)
- `instruction.md` template
- `source/app.py` with a minimal buggy function
- `source/test_visible.py` for local feedback
- `environment/Dockerfile` (python:3.12-slim)
- `evaluator/run_tests.sh` + `evaluator/tests/test_hidden.py` (stubs)
- `environment/Dockerfile` (python:3.12-slim)
- `solution/README.md` and `solution/files/app.py` (stubs)

The scaffold command materializes the repo from `source/`, pins the real commit in `task.toml`, and validates the task.

### 2. Manual task creation (alternative)

1. Create a source repo with a reproducible commit (fixed git identity/dates
   help). Pin the full SHA in `task.toml`; never use branches/tags.
2. Write `instruction.md` without hidden assertions.
3. Add hidden tests that fail on the starting commit and pass on the solution.
4. Keep evaluator files outside the agent workspace; the scheduler mounts them
   read-only only in the evaluator container.
5. Run `codebench tasks validate <id>` — metadata, paths (traversal rejected),
   commit existence, Dockerfile, evaluator command, timeouts.
6. Verify original fails and solution passes via the evaluator before scoring.

See `tasks/pilot/example-task/` for a runnable demo. Its `repo/` directory is
generated deterministically by test setup (`source/` + fixed git metadata) and
is gitignored; `task.toml` pins the resulting commit.

### 3. Task repository materialization

`codebench tasks materialize <id>` regenerates the task's `repo/` directory from
`source/` using fixed git metadata. This ensures the repo is always in a known
state. Use `--force` to regenerate, `--repin` to update the pinned commit in
`task.toml`.

### 4. Task verification

`codebench tasks verify <id>` checks that a task's oracle works correctly:
- Original commit fails the evaluator (hidden tests are a working oracle)
- Solution overlay passes the evaluator (reference solution is correct)

This catches broken oracles before running experiments.

### 5. Custom agents

Configure custom CLI agents in `benchmark.toml` under `[agents.custom.<name>]`:

```toml
[agents.custom.codex]
command = "codex"
args = ["--prompt", "{prompt}"]
output_format = "json"
model = ""
model_flag = "--model"
version_args = ["--version"]
timeout_seconds = 900
```

Then run with `--agents claude,codex` or `--agents all`.

See `docs/codebench-configuration.md` for full configuration reference.