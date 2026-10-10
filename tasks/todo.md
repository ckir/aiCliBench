# Todo: CodeBench Local MVP

## Task 1: Core statuses + schema contracts
**Description:** Add `RunStatus`/`EvalStatus`/`ErrorCategory` enums to `ai-core` and Pydantic v2 codebench records to `ai-schemas` (config, task, experiment/run/evaluation, usage normalization, capabilities).
**Acceptance criteria:**
- [ ] Enums cover spec §8 statuses + §11.1 eval outcomes, documented
- [ ] Schemas validate task.toml-equivalent, config defaults/overrides, invalid rejected
- [ ] No provider SDK/DB/network imports in core/schemas
**Verification:**
- [ ] Tests pass: `uv run pytest packages/core/tests packages/schemas/tests -q`
- [ ] Type check: `uv run ty check`
**Dependencies:** None
**Files likely touched:**
- `packages/core/src/ai_core/status.py`
- `packages/core/src/ai_core/__init__.py`
- `packages/schemas/src/ai_schemas/codebench.py`
- `packages/schemas/src/ai_schemas/__init__.py`
- `packages/core/tests/test_status.py`
- `packages/schemas/tests/test_codebench.py`
**Estimated scope:** Medium: 3-5 files

## Task 2: AgentAdapter protocol + RunResult + prompt wrapper + ordering
**Description:** Define `AgentAdapter` Protocol, `RunResult` dataclass, `AgentCapability`, error categorization, prompt wrapper (identical bytes, versioned, SHA-256), randomized paired ordering with seed in `ai-agents`.
**Acceptance criteria:**
- [ ] Subprocess arg-list contract, timeout/termination, defensive JSON parse guidance encoded
- [ ] Requested vs reported model separated; unknown/null handling
- [ ] Ordering reproducible with fixed seed
**Verification:**
- [ ] Tests pass: `uv run pytest packages/agents/tests -q`
**Dependencies:** Task 1
**Files likely touched:**
- `packages/agents/src/ai_agents/adapter.py`
- `packages/agents/src/ai_agents/__init__.py`
- `packages/agents/tests/test_adapter.py`
**Estimated scope:** Small: 1-2 files

## Task 3: Benchmark package skeleton + config + redaction + path safety
**Description:** Create `ai-benchmark` package (pyproject, README, `__init__`), implement `config.py` (benchmark.toml parsing/defaults/overrides/resolved snapshot), `redaction.py` (token patterns, no perfect claim), `paths.py` (traversal/symlink containment).
**Acceptance criteria:**
- [ ] Package independently buildable; deps only core/schemas/agents + stdlib (+pydantic)
- [ ] Invalid config rejected with actionable errors; resolved config recordable
- [ ] Redaction removes common secrets; traversal rejected
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests -q`
- [ ] Build: `uv build --package ai-benchmark`
**Dependencies:** Tasks 1-2
**Files likely touched:**
- `packages/benchmark/pyproject.toml`
- `packages/benchmark/src/ai_benchmark/*.py`
- `packages/benchmark/tests/test_*.py`
**Estimated scope:** Medium: 3-5 files

## Checkpoint: Foundation
- [ ] All tests pass
- [ ] Ruff + ty clean

## Task 4: Task registry
**Description:** `task_registry.py`: load/validate `task.toml` + `instruction.md`, path safety, commit hash full-length, Dockerfile/evaluator presence, instruction SHA-256, prompt wrapper identity.
**Acceptance criteria:**
- [ ] `tasks list` data available; `tasks validate` checks metadata/repo/commit/docker/tests/timeouts without running agent
- [ ] Directory traversal + symlink escapes rejected
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests/test_task_registry.py -q`
**Dependencies:** Task 3
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/task_registry.py`
- `packages/benchmark/tests/test_task_registry.py`
**Estimated scope:** Small

## Task 5: Git workspace manager
**Description:** `workspace.py`: clone/cache bare repo, checkout exact commit, verify hash, ensure clean, fresh dir per attempt, read-only object cache allowed.
**Acceptance criteria:**
- [ ] Every attempt starts from pinned commit; no shared writable checkout
- [ ] Starting commit + digests recorded
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests/test_workspace.py -q`
**Dependencies:** Task 4
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/workspace.py`
- `packages/benchmark/tests/test_workspace.py`
**Estimated scope:** Small

## Task 6: Docker runner
**Description:** `docker_runner.py`: build/pull images, agent-phase + evaluator-phase separate invocations, hardened flags (cpu/mem/pids, user, read-only rootfs, drop caps, no-new-privs, no socket), timeout + process-group kill, cleanup on success/failure/interrupt, local fallback for tests.
**Acceptance criteria:**
- [ ] Timeouts/ interrupts terminate container and preserve artifacts
- [ ] No docker socket/home/creds/hidden-tests mounts in agent phase
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests/test_docker_runner.py -q`
**Dependencies:** Task 5
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/docker_runner.py`
- `packages/benchmark/tests/test_docker_runner.py`
**Estimated scope:** Medium

## Task 7: Evaluator orchestration
**Description:** `evaluator.py`: copy snapshot/diff to fresh workspace, run trusted `evaluator_command` in evaluator container (no provider creds), capture exit/stdout/stderr/counts/build/lint/typecheck/regression, image/test-harness hashes.
**Acceptance criteria:**
- [ ] Agent self-report never authoritative; exit 0 → pass, non-zero → fail, infra failure → evaluation_error
- [ ] evaluation_error excluded from correctness denominator, reported separately
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests/test_evaluator.py -q`
**Dependencies:** Task 6
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/evaluator.py`
- `packages/benchmark/tests/test_evaluator.py`
**Estimated scope:** Medium

## Task 8: Fake agent + demo task fixture
**Description:** `fake_agent.py` for tests + root `tasks/pilot/example-task/` (task.toml, instruction.md, Dockerfile, run_tests.sh, tests/, solution README) backed by local git repo generated in test setup; original fails, solution passes.
**Acceptance criteria:**
- [ ] Demo validates end-to-end with fake agents (one pass, one failure)
- [ ] Placeholder external URL never shipped as real task
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests/test_demo.py -q`
**Dependencies:** Tasks 4-7
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/fake_agent.py`
- `tasks/pilot/example-task/**`
- `packages/benchmark/tests/test_demo.py`
**Estimated scope:** Medium

## Checkpoint: Core runner
- [ ] Demo validates; pass/fail detected; hidden tests isolated

## Task 9: Claude Code adapter
**Description:** `packages/integrations/claude-code`: non-interactive/print mode, structured-output probe, model flag only if documented, version/capability detection, defensive parse, usage only when returned.
**Acceptance criteria:**
- [ ] No shell interpolation; workspace as cwd; stdout/stderr to files; bounded terminal progress
- [ ] `unknown` model/cost when unverifiable; no bypass flags by default
**Verification:**
- [ ] Tests pass: `uv run pytest packages/integrations/claude-code/tests -q`
**Dependencies:** Tasks 2-3
**Files likely touched:**
- `packages/integrations/claude-code/pyproject.toml`
- `packages/integrations/claude-code/src/ai_integration_claude_code/*.py`
- `packages/integrations/claude-code/tests/test_*.py`
**Estimated scope:** Medium

## Task 10: Antigravity adapter
**Description:** `packages/integrations/antigravity`: `agy` non-interactive probe, stream-json capture + recognized event parse, model selection only when available, caps declaration.
**Acceptance criteria:**
- [ ] Same safety/integrity guarantees as Claude adapter; parity gaps shown, not faked
**Verification:**
- [ ] Tests pass: `uv run pytest packages/integrations/antigravity/tests -q`
**Dependencies:** Tasks 2-3
**Files likely touched:**
- `packages/integrations/antigravity/**`
**Estimated scope:** Medium

## Checkpoint: Adapters
- [ ] Success/non-zero/timeout/malformed/missing-fields/unsupported-flags/separation/metachar/termination covered

## Task 11: SQLite storage
**Description:** `storage.py`: experiments/runs/evaluations/artifacts tables, FK enforcement, transactions, schema_version migrations, no credentials/env dumps, usage-tolerant records.
**Acceptance criteria:**
- [ ] CRUD + migration + integrity tests; deterministic artifact hashes
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests/test_storage.py -q`
**Dependencies:** Task 8
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/storage.py`
- `packages/benchmark/tests/test_storage.py`
**Estimated scope:** Medium

## Task 12: Scheduler + doctor
**Description:** `scheduler.py` (sequential default, per-pair seed shuffle, fresh workspace, config snapshot+hashes, incomplete-pair reporting, no auto-retry, UTC ISO8601, host/tool versions, elapsed vs setup/eval split) + `doctor.py` (python/git/docker/CLIs/config/images/caps, no paid tasks) + interruption (`interrupted`, save artifacts, clean exit).
**Acceptance criteria:**
- [ ] Repeat N positive int default 1; Ctrl+C terminates container, marks interrupted
- [ ] Partial runs never labeled full comparison
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests/test_scheduler.py packages/benchmark/tests/test_doctor.py -q`
**Dependencies:** Tasks 9-11
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/scheduler.py`
- `packages/benchmark/src/ai_benchmark/doctor.py`
- `packages/benchmark/tests/test_scheduler.py`
- `packages/benchmark/tests/test_doctor.py`
**Estimated scope:** Medium

## Checkpoint: Persistence
- [ ] Reproducible order; interruption persists; cleanup verified

## Task 14: Scoring
**Description:** `scoring.py`: eligible/pass/pass_rate/task_solved/paired wins+ties/timeout-agent-setup-eval rates, runtime median+IQR (success only, timeouts capped separately), cost_per_success + coverage warnings, quality gates separate, bootstrap CI optional, no code-similarity grading.
**Acceptance criteria:**
- [ ] Denominators shown; invalid/eval-errors/missing never counted as failures
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests/test_scoring.py -q`
**Dependencies:** Task 11
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/scoring.py`
- `packages/benchmark/tests/test_scoring.py`
**Estimated scope:** Small

## Task 15: Reporting + export
**Description:** `reporting.py` (local-only static HTML via Jinja2 autoescape, 12 required sections, warnings for incomplete/unknown/uncomparable) + `export.py` (deterministic JSON/CSV + schema/version).
**Acceptance criteria:**
- [ ] All task/prompt/log output escaped; injection tests pass
- [ ] JSON/CSV deterministic, include metadata
**Verification:**
- [ ] Tests pass: `uv run pytest packages/benchmark/tests/test_reporting.py packages/benchmark/tests/test_export.py -q`
**Dependencies:** Task 14
**Files likely touched:**
- `packages/benchmark/src/ai_benchmark/reporting.py`
- `packages/benchmark/src/ai_benchmark/export.py`
- `packages/benchmark/src/ai_benchmark/templates/report.html`
- `packages/benchmark/tests/test_reporting.py`
- `packages/benchmark/tests/test_export.py`
**Estimated scope:** Medium

## Task 16: codebench Typer CLI
**Description:** `packages/cli` `codebench` entry: doctor/tasks list+validate/run/runs list/compare/report/export (+runs clean with dry-run/confirm), clear help/errors, stable exit codes, progress without secrets, no prompt/source dumps unless requested.
**Acceptance criteria:**
- [ ] `codebench --help` works clean-install; invalid config fails before agents; agent non-zero = result not crash
**Verification:**
- [ ] Tests pass: `uv run pytest packages/cli/tests -q`
**Dependencies:** Tasks 12,15
**Files likely touched:**
- `packages/cli/pyproject.toml`
- `packages/cli/src/ai_cli/codebench.py`
- `packages/cli/tests/test_codebench.py`
**Estimated scope:** Medium

## Task 17: Root config/tasks/docs/README
**Description:** `config/benchmark.toml` documented defaults, demo task finalization, `runs/` gitignore, docs (install/config/tasks/safety/interpretation + smoke-test + WSL2 note), README actual commands, `.env.example` safe placeholders only.
**Acceptance criteria:**
- [ ] Docs cover setup/auth/task creation/security/limits/interpretation; no unsupported flags or untested OS claims
- [ ] No secrets/artifacts/creds committed
**Verification:**
- [ ] Manual: `uv run codebench --help`, `codebench doctor`, `codebench tasks validate`
- [ ] Full: `uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run ty check && uv run pytest && uv build --all-packages`
**Dependencies:** Task 16
**Files likely touched:**
- `config/benchmark.toml`
- `tasks/pilot/example-task/**`
- `docs/**`
- `README.md`
- `.gitignore`
**Estimated scope:** Medium

## Checkpoint: Complete
- [ ] Spec §18 (1-18) verified line-by-line
- [ ] §20 security review (secrets/injection/traversal/mounts/errors/bounds)
- [ ] Completion standard commands green
