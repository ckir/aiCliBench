# Implementation Plan: CodeBench Local v0.1 Polish + v0.2 Enhancements

## Overview

Extend the completed MVP with pilot task suite, Docker pre-building, cost estimation, task validation, and v0.2 enhancements (resume, parallelism, regression detection, Markdown export, plugin scaffolding, MCP server). All work preserves monorepo architecture boundaries.

## Architecture Decisions

- **New `ai-cli` subcommands** extend existing `codebench` Typer app (no new packages)
- **Docker pre-build** adds `tasks build` command; reuses `docker_runner.build_image`
- **Cost estimation** uses static token/cost tables; no network calls
- **Resume** leverages existing SQLite `runs` table status; no schema changes
- **Parallelism** uses `concurrent.futures.ProcessPoolExecutor` with fresh workspaces; sequential default preserved
- **Plugin scaffolding** adds `codebench-gen` plugin via `ai-plugins-sdk` (new package under `packages/plugins/`)
- **MCP server** exposes read-only experiment queries via new `ai-mcp-codebench` server package
- **All v0.2 work** is additive; no breaking changes to MVP CLI or storage

## Task List

### Phase 1: v0.1 Polish (Pilot + Build + Estimate + Validate)

- [ ] Task 1: Pilot task suite scaffolding + 24 representative tasks
- [ ] Task 2: `codebench tasks build` — pre-build all task Docker images
- [ ] Task 3: `codebench estimate` — cost/time forecasting
- [ ] Task 4: `codebench tasks validate --build` — full validation with Docker build

### Checkpoint: v0.1 Polish
- [ ] `uv run pytest packages/benchmark/tests -q` green
- [ ] Pilot tasks validate end-to-end with fake agents
- [ ] `codebench tasks build --all` completes without manual steps

### Phase 2: v0.2 Core Enhancements (Resume + Parallel + Regression + Export)

- [ ] Task 5: `codebench runs resume` — re-run interrupted/failed only
- [ ] Task 6: `--parallelism N` — process-pool execution with fresh workspaces
- [ ] Task 7: `codebench compare --baseline` — regression detection
- [ ] Task 8: `codebench export --format md` — Markdown export

### Checkpoint: v0.2 Core
- [ ] Resume re-runs only failed/interrupted attempts
- [ ] `--parallelism 4` completes 4x faster (Docker permitting)
- [ ] Regression flagging works with clear thresholds
- [ ] Markdown export renders all 12 report sections

### Phase 3: v0.2 Extensions (Plugin + MCP + Schedule)

- [ ] Task 9: `packages/plugins/codebench-gen` — task scaffolding plugin
- [ ] Task 10: `packages/mcp-codebench` — MCP server for experiment queries
- [ ] Task 11: GitHub Actions scheduled nightly eval with live CLIs

### Checkpoint: Complete v0.2
- [ ] `codebench-gen init` scaffolds a valid task directory
- [ ] MCP server exposes `get_experiment`, `list_runs`, `compare_runs`
- [ ] Nightly workflow runs live CLIs and stores results separately

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Docker parallelism exhausts host resources | High | Limit `--parallelism` to CPU count; add `--docker-max-parallel` separate flag |
| Resume corrupts experiment state | High | Read-only query + new run IDs; never mutate existing runs |
| MCP server exposes sensitive run data | Med | Read-only queries; no artifact content; filter by experiment ownership if multi-user |
| Live evals consume provider credits | Med | Separate GitHub env with spend limits; run on schedule only |
| Plugin scaffold generates invalid tasks | Low | Template validates on `codebench tasks validate` immediately |

## Open Questions

- Pilot tasks: use your private repos or public ones with pinned commits?
- Cost estimation: static tables vs. optional provider API for current pricing?
- MCP server: auth model (token header? OAuth?) — MVP can start with header token

Tasks tracked in `tasks/todo-v0.2.md`.