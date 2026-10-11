# CodeBench trust fixes (v0.2 supplement) — design

Date: 2026-10-11. Branch: `feat/v0.2-trust-fixes`. Supplements `tasks/todo-v0.2.md`.

## Intent

The pilot suite now has 24 tasks, but nothing proves that a task's hidden tests
are a working oracle, the quality-gate flags every task declares are never
enforced, paired results carry no uncertainty, two of the 24 task repositories
cannot be regenerated from committed content, and only two hard-coded agents
can be benchmarked. These six items make the scores the tool already produces
trustworthy and make the harness agent-neutral.

Item 7 of the original recommendation (transcript capture) is **already
implemented**: both adapters write full stdout/stderr to `stdout.log` /
`stderr.log` and the scheduler indexes them (`scheduler.py` artifact index).
It is dropped from scope.

## Goals

1. Every pilot task is machine-verifiable: original commit fails the evaluator,
   the committed reference solution passes it. CI runs that check.
2. Every task repository is regenerated deterministically from committed
   `source/` content; the pinned commit is checked against the regeneration.
3. `[scoring]` build/lint/typecheck flags are enforced (or absent), recorded
   per evaluation, and reported separately from acceptance.
4. `compare` and the HTML report show uncertainty: a Wilson 95% interval per
   agent pass rate, an exact sign test on decisive pairs, and a paired
   bootstrap interval on the pass-rate difference.
5. A new task can be scaffolded with one command and verifies out of the box.
6. Any non-interactive CLI agent can be benchmarked through config alone.
7. Every experiment records a provenance manifest (image ids, environment
   digests, CLI versions, instruction/evaluator hashes); `tasks build` gets the
   digest cache, idempotent skip and digest table that Task 2 deferred.

## Non-goals / anti-goals

- No new benchmark tasks (separate decision for the user).
- No change to the acceptance test contract (`evaluator_command` stays the
  single trusted command). No grading of patch similarity.
- No parallelism, resume, Markdown export, MCP server or nightly workflow
  (those remain Tasks 3, 5–11 of the v0.2 todo).
- Do not make a gate "soft": a required gate that fails is a failed
  evaluation; an unconfigured gate is `None`, never `True`.
- Do not fabricate statistics for tiny samples: intervals are always shown
  with their n; a warning fires below 10 decisive pairs.
- The generic adapter must not weaken the existing two adapters or the
  hardened Docker path (`build_argv` contract preserved).

## Constraints (from AGENTS.md / repo)

- Dependencies flow inward; `ai_schemas` stays provider-free; no network at
  import; Pydantic v2 for externally validated data; frozen dataclasses for
  internal values; explicit exceptions with `from exc`.
- Gate: `uv run ruff check . && uv run ruff format --check . && uv run ty check
  --exclude "tasks/**/tests/*.py" --exclude "tasks/**/source/*.py" --exclude
  "tasks/**/evaluator/**/*.py" && uv run pytest --import-mode=importlib` and
  `uv build --all-packages`.
- Conventional Commits; release-please manifest must list any new package.
- `tasks/**/repo/` stays gitignored.

## Decided design

### D1. Task materialization (`ai_benchmark/task_materialize.py`)

- Recipe (the one the 24 repos were built with, measured from `git log`):
  author/committer `CodeBench Demo <demo@example.invalid>`, author and
  committer date `2026-01-01T00:00:00Z`, one commit, message `initial: <id>`,
  tree = every regular file under `<task>/source/` (recursive, sorted, no
  symlinks), copied byte-for-byte.
- `materialize_repo(task_dir, *, force=False) -> MaterializeResult(task_id,
  repo_path, commit, pinned_commit, action)` where `action` is `"kept"`
  (repo exists, HEAD == pinned), `"generated"` (created; HEAD == pinned), or
  raises `MaterializeMismatchError(expected, actual)` when the regenerated
  commit differs from `task.toml`. `force=True` deletes and regenerates.
  Only applies when `repository` is task-relative and `source/` exists;
  otherwise returns `action="skipped"`.
- `repin_task(task_dir, commit)` rewrites only the `^commit = "..."` line.
- Two existing tasks do not match the single-commit recipe and are repinned in
  this branch: `example-task` (message was `demo: buggy add`) and
  `semver-comparator` (two commits). `test_demo.py` switches to
  `materialize_repo` instead of its private recipe.
- CLI: `codebench tasks materialize [TASK_ID] [--suite S] [--force] [--repin]`.
  Exit 3 on mismatch without `--repin`.

### D2. Reference solutions as file overlays

- `solution/files/<path-relative-to-repo-root>` holds complete replacement (or
  new) files. `solution/README.md` stays as prose. Every pilot task gets an
  overlay (content derived from its README snippet and verified).
- `apply_solution(task_dir, workspace) -> list[Path]` copies the overlay onto a
  fresh checkout; rejects traversal via `safe_join`.

### D3. Oracle verification (`ai_benchmark/task_verify.py`)

- `verify_task(task_dir, *, work_dir, use_docker=False) -> TaskVerification(
  task_id, original: EvalStatus, solution: EvalStatus, ok, errors)`:
  materialize (no repin) → fresh checkout → evaluate (expect FAIL) → fresh
  checkout + overlay → evaluate (expect PASS with required gates passing).
  Missing overlay is an error. Uses `run_evaluation` with the task's
  `max_test_seconds`.
- CLI: `codebench tasks verify [TASK_ID] [--suite S] [--docker/--no-docker]`
  (default no-docker; never runs an agent). Exit 3 on any failure.
- Test: parametrized over every task dir under `tasks/pilot/`; this is the CI
  guard that a task is a working oracle.
- `validate_task` gains: error when `repository` is task-relative and
  `source/` is absent; warning when `solution/files/` is absent.

### D4. Quality gates enforced

- `TaskScoring` becomes: `acceptance_weight`, `build_required: bool = False`
  (default flips from True: a gate is opt-in), `lint_required: bool = False`,
  `typecheck_required: bool = False`, `build_command: list[str] = []`,
  `lint_command: list[str] = []`, `typecheck_command: list[str] = []`.
  Model validator: `X_required` ⇒ `X_command` non-empty.
- `run_evaluation` gains `gates: TaskScoring | None = None`. After the
  acceptance command (only when it did not time out), each configured gate
  command runs in the same eval workspace, same mode, same timeout.
  `EvaluatorResult` gains `build_pass`, `lint_pass`, `typecheck_pass`
  (`None` when not configured) and `gate_outputs: dict[str, str]` (tails).
  Semantics: `acceptance_pass` = acceptance test passed AND every *required*
  gate passed; a configured-but-not-required gate is recorded only. A gate
  that times out makes the whole evaluation `EVALUATION_ERROR`.
- Scheduler persists the three columns (already exist in SQLite) and the gate
  tails in `output_json`.
- Scoring `quality_gates[agent]` becomes
  `{acceptance_pass, eligible, build_pass, build_total, lint_pass, lint_total,
  typecheck_pass, typecheck_total}` where `*_total` counts evaluations where
  the gate was configured. Report §9 renders those columns.
- `example-task` gets a real gate: `build_required = true`,
  `build_command = ["python3", "-m", "compileall", "-q", "."]`.

### D5. Statistics (`ai_benchmark/scoring.py`)

- `wilson_interval(successes, n, z=1.959964) -> (low, high) | None` (None when
  n == 0). `CorrectnessSummary.pass_rate_ci95`.
- `sign_test_p_value(a_wins, b_wins) -> float | None`: exact two-sided
  binomial test, p = 0.5, over decisive pairs; None when no decisive pairs.
  `PairedSummary.sign_test_p_value`.
- `paired_bootstrap_delta_ci(outcomes, *, resamples=2000, seed=20261010)`
  over per-pair `(pass_a, pass_b)` tuples; returns the 2.5/97.5 percentile of
  mean(pass_a − pass_b). Deterministic. `PairedSummary.delta_ci95` and
  `PairedSummary.decisive_pairs`.
- `compare` prints CI, p-value and delta CI; report §3 adds a CI column, §4
  adds the paired statistics and a caution line when decisive pairs < 10.

### D6. Task scaffold (`ai_benchmark/task_scaffold.py`, `codebench tasks init`)

- `scaffold_task(tasks_root, *, task_id, suite="pilot", title, category,
  description="") -> Path` writes the standard layout with a tiny but complete
  example (a buggy function in `source/`, a visible test, a hidden test that
  fails on the stub, the standard `run_tests.sh`, Dockerfile, `solution/files/`
  overlay and README), then materializes and pins the commit. Refuses to
  overwrite an existing task dir.
- CLI: `codebench tasks init TASK_ID --title T --category C [--suite S]
  [--description D]`. Result passes `validate` and `verify` immediately.
  Replaces the never-written `tasks/generator.py`.

### D7. Generic CLI adapter (`packages/integrations/generic-cli`)

- Package `ai-integration-generic-cli`, module `ai_integration_generic_cli`.
- `GenericCliConfig(command, args: list[str] = [], output_format:
  Literal["json","jsonl","text"] = "text", model="", model_flag="",
  version_args: list[str] = ["--version"], timeout_seconds=900)`.
  `args` may contain the token `{prompt}`; if absent, the prompt is appended
  as the final argument. `model_flag` + `model` are appended when both are set.
  No shell; argv list only.
- `GenericCliAdapter` implements `AgentAdapter` plus `build_argv(prompt)` so
  the hardened Docker path works unchanged. Parsing: `json` → one object
  (`result`/`content`/`text`, `model`, `usage{...}`), `jsonl` → last
  parseable object with those keys (unknown events skipped), `text` → raw.
  Unknown fields never crash; missing usage is `None`.
- Config: `AgentsConfig.custom: dict[str, CustomAgentConfig] = {}`; names must
  match `^[a-z][a-z0-9_-]{0,31}$` and not be `claude`/`antigravity`.
  `enabled_agents()` includes enabled custom names. `--agents` accepts
  `all|claude|antigravity|<name>` or a comma-separated list. `doctor` checks
  each custom command. Paired statistics apply only when exactly two agents
  ran (unchanged).
- Wiring: root `pyproject.toml` deps/sources, `packages/cli` deps,
  release-please config + manifest, `docs/codebench-configuration.md`.

### D8. Provenance manifest + build cache (`ai_benchmark/provenance.py`)

- `environment_digest(task_dir, dockerfile_rel) -> str`: sha256 over the
  Dockerfile bytes and every file under `source/` (sorted relative path +
  bytes). Independent of Docker.
- `inspect_image(tag) -> ImageInfo(id, size_bytes) | None` via
  `docker image inspect --format '{{.Id}} {{.Size}}'`.
- `ImageCache` at `.codebench/images.json` (cwd-relative, gitignored):
  `{task_id: {tag, environment_digest, image_id, size_bytes, built_at}}`.
- `tasks build`: compute digest; skip as `cached` when the cache entry matches
  and the image id still exists; `--force` rebuilds; prints a table
  `task_id  image  digest(12)  size`.
- Scheduler: fills `runs.environment_digest` for every run; in Docker mode
  also the image id (in `metadata.json`). At experiment end writes
  `runs/<exp>/manifest.json` and stores it in a new `experiments.provenance_json`
  column (`{"prompt_wrapper_version", "docker", "agents": {name: {cli_version,
  requested_model}}, "tasks": {id: {commit, instruction_sha256,
  evaluator_digest, environment_digest, image_id}}}`).
- Storage: `SCHEMA_VERSION = 2`; `connect` applies forward migrations
  (`ALTER TABLE experiments ADD COLUMN provenance_json TEXT NOT NULL DEFAULT
  '{}'`) and still rejects a newer version. `ExperimentRecord.provenance`.
- Report §1 shows the manifest summary; JSON export carries it via the row.

## Left to the builder

- Exact wording of CLI output lines, test fixture layout, helper naming.
- Where the shared "standard run_tests.sh" template lives (suggest a constant
  in `task_scaffold.py`).

## Sequencing

Wave 1 (disjoint files): D4 gates · D1 materialize+repin · D7 generic adapter.
Wave 2: D5 statistics · D3 verify (+ D2 apply) · D8 provenance/build cache.
Wave 3: D2 overlays for all 24 tasks (parallel batches, each verified) · D6 scaffold.
Final: docs, todo update, full gate, `uv build --all-packages`.

## Builder-check decisions (2026-10-11, settled by the author)

1. `GenericCliAdapter(name, config)`: the agent name is injected at
   construction and must equal the config key. `BenchmarkConfig._check_timeouts`
   also checks every custom agent. The Docker agent path (`_run_agent_in_docker`)
   keeps its current contract; the task image lacking agent binaries is a
   pre-existing limitation, out of scope here.
2. `--agents all` = `AgentsConfig.enabled_agents()` (built-ins plus enabled
   custom agents). Paired statistics are computed only when exactly two agents
   ran; `run` prints a note when more than two are selected.
3. Materialization is implicit: `validate_task(check_repo=True)` and the
   scheduler's `_run_once` call `materialize_repo(task_dir)` before touching the
   repository. `kept` additionally requires a clean worktree (`git status
   --porcelain` empty); a dirty repo raises `ConfigurationError` unless `force`.
4. Gate semantics: gates run whenever the acceptance command returned an exit
   code (pass or fail), never after an acceptance timeout. Acceptance test pass
   + required gate fail ⇒ `status = FAIL`, `acceptance_pass = False`. A timeout
   of any *configured* gate ⇒ `status = EVALUATION_ERROR`, `acceptance_pass =
   None`.
5. Digests (`evaluator_digest`, `environment_digest`) skip `__pycache__`,
   `*.pyc` and `.pytest_cache`. Changing `evaluator_digest` is allowed (no
   released databases). Local-mode evaluation sets `PYTHONDONTWRITEBYTECODE=1`.
6. No-docker `verify` inherits `PATH`, so under `uv run` the venv `python3`
   (with pytest) is used; documented as the supported way to run it.
7. Paired bootstrap runs over all valid pairs (both evaluations present and
   neither an evaluation error); delta = mean(pass_A − pass_B) with A, B the
   alphabetically sorted agent names, labelled in output.
8. `connect` applies forward migrations in order inside a transaction and
   inserts a new `schema_version` row per applied version; migration 1→2 adds
   `experiments.provenance_json` (guarded by `PRAGMA table_info`). Fresh
   databases get the column from `_SCHEMA` directly.
9. `CustomAgentConfig` lives in `ai_schemas` (no integration import);
   `GenericCliConfig` in the integration package mirrors its fields.
