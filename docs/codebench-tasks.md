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

Steps:

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
