# Implementation Plan: CodeBench Local MVP (v0.1)

## Overview

Implement `MVP/codebench_local_mvp_spec.md` (codebench-local v0.1.0) inside this AI/MCP/plugin monorepo while preserving `AGENTS.md` / `ARCHITECTURE.md` dependency rules. The tool compares Claude Code CLI vs Google Antigravity CLI (`agy`) on pinned repo tasks with Docker-isolated agent + evaluator phases, SQLite persistence, paired randomized trials, and static HTML/JSON/CSV reporting.

Spec is approved source of truth. This plan maps spec §19 milestones to monorepo packages.

## Architecture Decisions

- **Spec module → monorepo mapping (spec §5 allows reorganization with clear separation):**
  - `src/codebench/models.py` → `packages/schemas/src/ai_schemas/codebench.py` (Pydantic v2, no provider/DB/network deps)
  - Statuses (`RunStatus`, `EvalStatus`, `ErrorCategory`) → `packages/core/src/ai_core/status.py` (stdlib only, dependency-light)
  - `agents/base.py` (`AgentAdapter`, `RunResult`, `Capability`) → `packages/agents/src/ai_agents/adapter.py` (depends only on core/schemas)
  - `agents/claude_code.py` → `packages/integrations/claude-code/src/ai_integration_claude_code/` (CLI subprocess adapter, like `integrations/openai`)
  - `agents/antigravity.py` → `packages/integrations/antigravity/src/ai_integration_antigravity/`
  - `config.py`, `task_registry.py`, `workspace.py`, `docker_runner.py`, `evaluator.py`, `scheduler.py`, `scoring.py`, `storage.py`, `reporting.py`, `export.py`, `redaction.py`, `doctor.py` → new `packages/benchmark/src/ai_benchmark/` (domain + persistence + execution; depends on core/schemas/agents, never the reverse)
  - `cli.py` (`codebench` command) → `packages/cli/src/ai_cli/codebench.py` (Typer; composes benchmark + integrations)
  - Demo task + `config/benchmark.toml` at repo root (`tasks/pilot/example-task/`, `config/`), `runs/` gitignored.
- **Why new `ai-benchmark` package instead of stuffing into `ai-evals`:** `ai-evals` is generic deterministic eval framework (cases/runner). CodeBench is a specific Docker/SQLite/CLI product with persistence. Separate package = explicit boundary, independently releasable, keeps `evals` generic. `ai-benchmark` depends on `ai-agents`, `ai-core`, `ai-schemas`; `ai-cli` depends on `ai-benchmark` + integrations.
- **Validation:** Pydantic v2 consistently for config/result records (§3.2). `tomllib` stdlib for TOML (py>=3.12). `typer` for CLI, `jinja2` for HTML (escaped). `sqlite3`, `subprocess` (arg lists only), `pathlib`, `hashlib` stdlib for core ops. No ORM.
- **Security (fail-closed):** agent phase and evaluator phase are separate container invocations; never mount docker socket, home, credentials wholesale, or hidden tests into agent; default network off; CPU/mem/pids limits, non-root user, read-only rootfs where supported, drop caps, no-new-privs; subprocess arg lists only; path traversal/symlink checks; redaction (no perfect-redaction claim); `workspace_cleanup=retain` under data dir.
- **Honesty:** missing model/usage/cost → `unknown`/`null`/`not available`, never invented; CLI-system comparison, not model isolation claim.

## Task List

### Phase 1: Foundation (schemas/core/agents contracts)

- [ ] Task 1: Core statuses + schema contracts
- [ ] Task 2: AgentAdapter protocol + RunResult + prompt wrapper + ordering util
- [ ] Task 3: Benchmark package skeleton + config + redaction + path safety

### Checkpoint: Foundation
- [ ] `uv run ruff check .`, `ruff format --check`, `ty check`, focused `pytest` green

### Phase 2: Task + workspace + docker + evaluator (Milestone 1)

- [ ] Task 4: Task registry (TOML validation, traversal rejection, instruction SHA)
- [ ] Task 5: Git workspace manager (pin, fresh per attempt, read-only cache)
- [ ] Task 6: Docker runner (hardened flags, timeout, cleanup, non-docker fallback for tests)
- [ ] Task 7: Evaluator orchestration (read-only snapshot, separate container, result fields)
- [ ] Task 8: Fake agent for integration tests + demo task fixture (local git repo, pass/fail)

### Checkpoint: Core runner
- [ ] Demo validates; fake-agent pass + fail detected; hidden tests not accessible to agent

### Phase 3: Provider adapters (Milestone 2)

- [ ] Task 9: Claude Code adapter (print mode, structured output defensive parse, version/caps)
- [ ] Task 10: Antigravity adapter (`agy`, stream-json defensive parse, version/caps)

### Checkpoint: Adapters
- [ ] Fake-executable tests: success, non-zero, timeout, malformed JSON, missing fields, shell-metachar prompt, termination

### Phase 4: Experiments + persistence (Milestone 3)

- [ ] Task 11: SQLite storage (experiments/runs/evaluations/artifacts, migrations, transactions, FK)
- [ ] Task 12: Scheduler (paired randomized order with seed, repeats, fresh workspace, interrupt handling, artifact hashes)
- [ ] Task 13: Doctor checks

### Checkpoint: Persistence
- [ ] Migration + transaction tests; scheduler reproducibility; Ctrl+C → interrupted + artifacts

### Phase 5: Metrics + reports + CLI (Milestone 4)

- [ ] Task 14: Scoring (pass_rate denominators, paired wins, timeout/error rates, cost coverage, quality gates)
- [ ] Task 15: Reporting (escaped HTML, required 12 sections) + export (deterministic JSON/CSV)
- [ ] Task 16: `codebench` Typer CLI (doctor/tasks/run/runs/compare/report/export, exit codes, no secret dumps)
- [ ] Task 17: Root `config/benchmark.toml`, `tasks/pilot/example-task/`, `runs/` gitignore, docs (install/config/tasks/safety/interpretation), README actual commands

### Checkpoint: Complete
- [ ] `uv sync --locked`, `ruff check`, `ruff format --check`, `ty check`, `pytest`, `uv build --all-packages` green
- [ ] Spec §18 acceptance 1-18 verified; §20 review (secrets, injection, traversal, mounts, errors, bounds)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Installed `claude`/`agy` flags differ from spec examples | High | Verify via `--help`/docs at runtime; adapters probe caps, never assume flags; record unresolved as default/unknown |
| Docker unavailable in CI/test env | Med | `docker_runner` supports local-process fallback for unit tests; Docker-gated integration tests skipped without docker, demo Dockerfile builds offline after deps |
| Credential mount safety not feasible | High | Fail-closed diagnostic, refuse run, document exposure; never copy creds to artifacts |
| SQLite concurrency | Low | Sequential default (`parallelism=1`); transactions + FK; no parallel by default |
| HTML injection via task/prompt/logs | High | Escape all user/task text in Jinja2 (autoescape) + tests |
| Small pilot over-claimed | Med | Report denominators, invalid/missing pairs, warnings; no winner from tiny diffs |

## Open Questions

- None blocking MVP: model-price scraping out of scope; subscription cost → `not available` with optional user estimate labeled as such.
- WSL2/Windows: document WSL2+Docker path only; claim native support only if tested.

Tasks tracked in `tasks/todo.md` (default markdown target; no external tracker designated).
