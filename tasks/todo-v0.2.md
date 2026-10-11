# Todo: CodeBench Local v0.1 Polish + v0.2 Enhancements

## Task 1: Pilot task suite scaffolding + 24 representative tasks
**Description:** Create a `tasks/generator.py` script that scaffolds task directories from a template, then populate `tasks/pilot/` with 24 tasks from your repos (pinned commits, hidden tests, evaluator). Each task validates via `codebench tasks validate`.
**Acceptance criteria:**
- [ ] Generator creates valid task structure (task.toml, instruction.md, Dockerfile, evaluator/, solution/)
- [ ] 24 tasks under `tasks/pilot/` with unique IDs, categories, pinned commits
- [ ] All 24 pass `codebench tasks validate <id>`
- [ ] At least 5 categories represented (bugfix, feature, refactor, test, perf)
**Verification:**
- [ ] `uv run codebench tasks list --suite pilot` shows 24 tasks
- [ ] `uv run codebench tasks validate <each>` all pass
- [ ] Fake agents produce mixed pass/fail for variety
**Dependencies:** None
**Files likely touched:**
- `tasks/generator.py`
- `tasks/pilot/*/task.toml`
- `tasks/pilot/*/instruction.md`
- `tasks/pilot/*/environment/Dockerfile`
- `tasks/pilot/*/evaluator/run_tests.sh`
- `tasks/pilot/*/evaluator/tests/`
- `tasks/pilot/*/solution/README.md`
**Estimated scope:** Large: 5+ files per task (24 tasks = many files, but generator automates)

## Task 2: `codebench tasks build` — pre-build all task Docker images
**Description:** Add `build` subcommand to `tasks` Typer group. Iterates all tasks in a suite, runs `docker build` for each `environment/Dockerfile`, records image digest in a local cache file (`.codebench/images.json`), skips if digest matches.
**Acceptance criteria:**
- [ ] `codebench tasks build --suite pilot` builds all task images
- [ ] `--all` flag builds across all suites
- [ ] Outputs digest table: task_id, image, digest, size
- [ ] Idempotent: re-run skips unchanged (digest match)
- [ ] Validates `Dockerfile` exists before build
**Verification:**
- [ ] `uv run codebench tasks build --suite pilot` completes
- [ ] Re-run shows "skipped (cached)" for all
- [ ] `docker images` shows built images
**Dependencies:** Task registry, docker_runner
**Files likely touched:**
- `packages/cli/src/ai_cli/codebench.py` (tasks_app add build)
- `packages/benchmark/src/ai_benchmark/docker_runner.py` (build_image reused)
- `packages/benchmark/tests/test_docker_build.py` (new)
**Estimated scope:** Medium: 3-5 files

## Task 3: `codebench estimate` — cost/time forecasting
**Description:** Add `estimate` command. Given `--task X --repeat N --agents all`, estimates total wall time, API cost (using static tables: claude ~$0.01/1k tokens, antigravity ~$0.008), Docker overhead. Uses historical median runtime from SQLite if available, else defaults (300s/agent).
**Acceptance criteria:**
- [ ] `codebench estimate --task example-task --repeat 3` prints table
- [ ] Columns: agent, estimated_runs, est_time_per_run, est_total_time, est_cost_usd
- [ ] Falls back to defaults when no history
- [ ] Shows "unknown" for subscription plans without per-run telemetry
**Verification:**
- [ ] `uv run codebench estimate --task example-task --repeat 3` runs
- [ ] Output includes all agents from config
- [ ] Cost labeled "estimate" not "actual"
**Dependencies:** Scoring (for historical medians), config
**Files likely touched:**
- `packages/cli/src/ai_cli/codebench.py` (new estimate command)
- `packages/benchmark/src/ai_benchmark/scoring.py` (add estimate helper)
- `packages/cli/tests/test_estimate.py` (new)
**Estimated scope:** Medium: 3-5 files

## Task 4: `codebench tasks validate --build` — full validation with Docker build
**Description:** Extend `tasks validate` with `--build` flag that runs `docker build` for the task's Dockerfile and a dry-run of the evaluator (no agent). Validates: task.toml schema, paths, commit exists, Dockerfile builds, evaluator script executable, hidden tests not in instruction.
**Acceptance criteria:**
- [ ] `codebench tasks validate example-task --build` runs docker build
- [ ] Fails fast on Dockerfile syntax errors
- [ ] Runs evaluator with `--dry-run` flag (exits 0 without tests)
- [ ] Reports build time and image size
**Verification:**
- [ ] `uv run codebench tasks validate example-task --build` passes
- [ ] Invalid Dockerfile causes clear error
- [ ] Dry-run evaluator doesn't run actual tests
**Dependencies:** Task 2 (build_image), evaluator
**Files likely touched:**
- `packages/cli/src/ai_cli/codebench.py` (tasks validate --build)
- `packages/benchmark/src/ai_benchmark/task_registry.py` (validate_task add build check)
- `packages/benchmark/tests/test_task_validate_build.py` (new)
**Estimated scope:** Medium: 3-5 files

## Checkpoint: v0.1 Polish
- [ ] All 24 pilot tasks validate end-to-end
- [ ] `codebench tasks build --suite pilot` completes
- [ ] `codebench estimate --task example-task --repeat 3` works
- [ ] `codebench tasks validate example-task --build` passes

## Task 5: `codebench runs resume` — re-run interrupted/failed only
**Description:** Add `resume` subcommand to `runs` group. Given `--experiment ID`, finds runs with status `interrupted`, `timeout`, `agent_error`, `setup_error`, re-executes them with fresh workspaces, preserves completed runs. New runs get new IDs; original statuses unchanged.
**Acceptance criteria:**
- [ ] `codebench runs resume --experiment exp_xxx` re-runs only failed/interrupted
- [ ] Completed runs (`status=completed` + eval `pass`/`fail`) skipped
- [ ] New run IDs created; experiment `total_runs` increments
- [ ] `--dry-run` shows what would be re-run without executing
**Verification:**
- [ ] Create experiment, kill one run, resume re-runs only that one
- [ ] Completed runs unchanged in DB
- [ ] `--dry-run` lists correct run IDs
**Dependencies:** Scheduler, storage
**Files likely touched:**
- `packages/cli/src/ai_cli/codebench.py` (runs resume)
- `packages/benchmark/src/ai_benchmark/scheduler.py` (add resume logic)
- `packages/benchmark/src/ai_benchmark/storage.py` (query failed runs)
- `packages/benchmark/tests/test_resume.py` (new)
**Estimated scope:** Medium: 3-5 files

## Task 6: `--parallelism N` — process-pool execution with fresh workspaces
**Description:** Add `--parallelism N` flag to `run` command (overrides config). Uses `ProcessPoolExecutor` with `N` workers; each worker gets fresh workspace, sequential agent execution per worker. Docker concurrency limited by `--docker-max-parallel` (default: CPU count). Progress bar shows worker status.
**Acceptance criteria:**
- [ ] `codebench run --task X --agents all --repeat 2 --parallelism 4` runs
- [ ] Workers isolated: separate workspaces, no shared state
- [ ] `--docker-max-parallel 2` limits concurrent containers
- [ ] Progress: `[worker 1/4] example-task:1 claude...`
- [ ] Sequential fallback (`parallelism=1`) unchanged
**Verification:**
- [ ] `uv run codebench run --task example-task --agents all --repeat 2 --parallelism 2` completes
- [ ] Wall time < sequential for same work
- [ ] No workspace collisions (check `runs/exp_*/run_*/workspace`)
**Dependencies:** Scheduler (refactor to worker function), docker_runner
**Files likely touched:**
- `packages/cli/src/ai_cli/codebench.py` (run --parallelism)
- `packages/benchmark/src/ai_benchmark/scheduler.py` (worker fn, pool)
- `packages/benchmark/tests/test_parallel.py` (new)
**Estimated scope:** Medium: 3-5 files

## Task 7: `codebench compare --baseline` — regression detection
**Description:** Add `--baseline EXP_ID` to `compare`. Compares current experiment vs baseline: per-task pass rate delta, runtime delta, new failures. Flags tasks where pass rate dropped > 10% or new timeout/agent_error. Exit code 1 if regressions found.
**Acceptance criteria:**
- [ ] `codebench compare --latest --baseline exp_abc` shows delta table
- [ ] Columns: task, agent, baseline_pass, current_pass, delta%, baseline_time, current_time, delta%
- [ ] Red highlight (ANSI) for regressions >10%
- [ ] `--threshold 0.05` to adjust sensitivity
- [ ] Exit 1 if any regression above threshold
**Verification:**
- [ ] Run baseline exp, then modify task to break, run current, compare flags regression
- [ ] Exit code 1 on regression
- [ ] Output clearly shows which task/agent regressed
**Dependencies:** Scoring, storage
**Files likely touched:**
- `packages/cli/src/ai_cli/codebench.py` (compare --baseline)
- `packages/benchmark/src/ai_benchmark/scoring.py` (add regression_delta)
- `packages/cli/tests/test_compare_baseline.py` (new)
**Estimated scope:** Medium: 3-5 files

## Task 8: `codebench export --format md` — Markdown export
**Description:** Add `--format md` to `export`. Renders the 12-section HTML report as Markdown (tables, headers, code fences). Suitable for GitHub PR comments, Notion, Obsidian.
**Acceptance criteria:**
- [ ] `codebench export --latest --format md -o report.md` creates valid .md
- [ ] All 12 sections present with same data as HTML
- [ ] Tables render as GitHub-flavored markdown
- [ ] Code fences for config JSON
- [ ] Links to local artifact files use relative paths
**Verification:**
- [ ] `uv run codebench export --latest --format md` outputs to stdout
- [ ] `cat report.md | pandoc -f markdown -t html` renders without error
- [ ] Data matches `export --format json`
**Dependencies:** Reporting (reuse data prep)
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/export.py` (add markdown renderer)
- `packages/benchmark/src/ai_benchmark/reporting.py` (shared data prep)
- `packages/cli/src/ai_cli/codebench.py` (export --format md)
- `packages/benchmark/tests/test_export_md.py` (new)
**Estimated scope:** Medium: 3-5 files

## Checkpoint: v0.2 Core
- [ ] `codebench runs resume` re-runs only failed
- [ ] `--parallelism 4` works with progress bar
- [ ] `--baseline` flags regressions with exit 1
- [ ] `--format md` renders all 12 sections

## Task 9: `packages/plugins/codebench-gen` — task scaffolding plugin
**Description:** New package under `packages/plugins/codebench-gen/` implementing `ai-plugins-sdk.Plugin`. Provides `codebench-gen init` tool (or `codebench task init` subcommand) that scaffolds a task directory from a template: prompts for repo URL, commit, category; creates task.toml, instruction.md, Dockerfile, evaluator stub, solution/README.
**Acceptance criteria:**
- [ ] `uv run codebench task init --interactive` prompts and creates task
- [ ] `uv run codebench task init --repo URL --commit SHA --category bugfix` non-interactive
- [ ] Generated task passes `codebench tasks validate`
- [ ] Template includes: pinned commit, Dockerfile with python:3.12-slim, evaluator with pytest, solution README
- [ ] Plugin registered via `ai-plugins-sdk` entry point
**Verification:**
- [ ] `uv run codebench task init --repo https://github.com/user/repo --commit abc123 --category feature` creates valid task
- [ ] `codebench tasks validate <new-task>` passes
- [ ] Plugin discoverable via `PluginRegistry`
**Dependencies:** ai-plugins-sdk, task_registry
**Files likely touched:**
- `packages/plugins/codebench-gen/pyproject.toml`
- `packages/plugins/codebench-gen/src/ai_plugin_codebench_gen/`
- `packages/plugins/codebench-gen/tests/`
- `packages/cli/src/ai_cli/codebench.py` (task init subcommand)
**Estimated scope:** Medium: 5+ files (new package)

## Task 10: `packages/mcp-codebench` — MCP server for experiment queries
**Description:** New package `packages/mcp-codebench/` implementing `McpServer` from `ai-mcp-server`. Exposes tools: `get_experiment(id)`, `list_experiments(limit)`, `list_runs(experiment_id)`, `compare_runs(experiment_id, baseline_id?)`, `get_run_artifacts(run_id)`. Read-only; no artifact content (links only).
**Acceptance criteria:**
- [ ] `uv run mcp-codebench-server` starts stdio server
- [ ] `get_experiment` returns full experiment record
- [ ] `list_experiments` supports `limit`, `status` filter
- [ ] `compare_runs` returns same delta as CLI `compare`
- [ ] No write tools; all `effect=READ`
- [ ] Configurable SQLite path via env `CODEBENCH_DB`
**Verification:**
- [ ] `uv run mcp-codebench-server` starts, `mcp-cli tools` lists 5 tools
- [ ] `mcp-cli call get_experiment '{"id":"exp_xxx"}'` returns JSON
- [ ] Tools have proper input/output schemas
**Dependencies:** ai-mcp-server, ai-mcp-core, storage
**Files likely touched:**
- `packages/mcp-codebench/pyproject.toml`
- `packages/mcp-codebench/src/ai_mcp_codebench/`
- `packages/mcp-codebench/tests/`
- `packages/mcp-codebench/Dockerfile` (optional)
**Estimated scope:** Medium: 5+ files (new package)

## Task 11: GitHub Actions scheduled nightly eval with live CLIs
**Description:** Add `.github/workflows/nightly-eval.yml`. Runs `codebench run --suite pilot --agents all --repeat 1` on schedule (daily 2am UTC). Uses separate GitHub env `nightly` with `CLAUDE_API_KEY`, `AGY_API_KEY` secrets. Stores results in `nightly-runs/` artifact. Fails workflow on regression vs last successful run (uses `compare --baseline`).
**Acceptance criteria:**
- [ ] Workflow runs daily at 2am UTC (cron)
- [ ] Uses `nightly` environment with required secrets
- [ ] Uploads `nightly-runs/exp_*/` as artifact
- [ ] Posts summary comment on scheduled run with pass rates
- [ ] Fails on regression (exit 1 from compare --baseline)
- [ ] Does not run on PRs (schedule only)
**Verification:**
- [ ] Manual `workflow_dispatch` triggers run
- [ ] Artifacts contain experiment SQLite + reports
- [ ] Regression detection works when task breaks
**Dependencies:** CI passing, live CLI auth configured
**Files likely touched:**
- `.github/workflows/nightly-eval.yml`
- `scripts/nightly_eval.sh` (optional wrapper)
**Estimated scope:** Small: 1-2 files

## Checkpoint: Complete v0.2
- [ ] `codebench-gen` plugin scaffolds valid tasks
- [ ] MCP server exposes 5 read-only tools
- [ ] Nightly workflow runs and posts summary

## Final Verification (All Phases)
- [ ] `uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run ty check --exclude "tasks/**/tests/*.py" --exclude "tasks/**/source/*.py" --exclude "tasks/**/evaluator/**/*.py" && uv run pytest --import-mode=importlib -q`
- [ ] `uv build --all-packages` succeeds
- [ ] All checkpoints green