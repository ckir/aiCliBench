# CodeBench Local — MVP Implementation Specification

**Document type:** Implementation-ready MVP specification  
**Project name:** `codebench-local`  
**Version:** 0.1.0  
**Status:** Ready for coding-agent implementation  
**Primary objective:** Determine which of Claude Code and Google Antigravity CLI delivers better results on the user's everyday programming tasks, using repeatable, independently graded experiments on a local development machine.

---

## 1. Product summary

Build a local-first command-line tool that runs the same software-engineering tasks against two coding agents:

1. Claude Code CLI.
2. Google Antigravity CLI (`agy`).

Each run starts from a pinned repository state, gives the agent a task prompt and bounded execution time, captures its outputs and resulting diff, then evaluates the change with tests that the agent cannot modify. The tool stores experiment metadata and artifacts, calculates comparable metrics, and generates a static HTML report plus JSON/CSV exports.

The MVP must measure **the combined practical performance of each CLI, its configured model, its agent harness, and its available tools**. It must not claim to isolate the underlying model unless a separate controlled experiment explicitly holds the harness and tools constant.

### 1.1 MVP principles

- Correctness and useful delivery matter more than generated-code volume.
- Both agents receive the same task text and equivalent task environments.
- Evaluation is independent of the agent and its self-reported success.
- Runs are reproducible from recorded inputs as far as the providers permit.
- Missing usage/cost data is marked unknown, never invented.
- Failures, timeouts, and interrupted runs are recorded, not silently discarded.
- Local execution is the primary deployment target.
- Prefer a small, maintainable implementation over a large platform.
- Never run agents with unrestricted host access as a benchmark default.

## 2. Scope

### 2.1 Required in v0.1

- Python command-line application.
- Claude Code and Antigravity CLI adapters.
- Adapter health checks and version capture.
- Versioned task definitions in TOML plus Markdown instructions.
- Git-based task repositories pinned to commit hashes.
- Fresh workspace per attempt.
- Docker-backed isolated agent execution and separate evaluator execution.
- Per-run wall-clock timeout and container resource limits.
- Capture standard output, standard error, structured events where available, exit status, diff, test output, and metadata.
- SQLite experiment/run database.
- Repeated paired trials and randomized agent order.
- Independent evaluator running hidden acceptance tests.
- Metrics for correctness, runtime, timeouts, failure categories, and usage/cost when available.
- Static HTML report, JSON export, CSV export.
- Unit and integration tests for orchestration, adapters, scoring, and evaluator isolation.
- Documentation for installation, configuration, adding tasks, safety, and interpreting results.

### 2.2 Explicitly out of scope for v0.1

- Hosted service, multi-user accounts, or cloud dashboard.
- Distributed workers or parallel execution by default.
- Automated task generation by an LLM.
- Subjective AI code review as a primary score.
- Public leaderboard.
- Automatic model-price scraping.
- Perfectly isolating model quality from CLI/harness differences.
- Windows-native sandboxing. Windows users may run the tool through WSL2 with Docker, but this must be documented and tested if claimed as supported.
- Automatic recovery/retry after an agent failure. Failed attempts are recorded; retries are separate attempts so failure rates remain visible.

## 3. Supported environment and technology

### 3.1 Primary environment

- Python 3.12 or newer.
- Git.
- Docker Engine/Desktop with a working Linux-container backend.
- Installed and authenticated Claude Code CLI.
- Installed and authenticated Google Antigravity CLI (`agy`).
- Linux and macOS should be targeted first. Windows support is via WSL2 + Docker only unless the implementation explicitly tests native support.

### 3.2 Dependencies

Use a minimal set of well-maintained packages:

- `typer` for CLI.
- `pydantic` or standard-library validation for configuration and result records; choose one approach consistently.
- `tomllib` for reading TOML (Python 3.11+); use `tomli` only if supporting older Python is explicitly required.
- `jinja2` for HTML report templating, with all user/task text escaped.
- `pytest` for tests.
- `ruff` for linting.
- Optional `pytest-cov` for test coverage.

Prefer `sqlite3`, `subprocess`, `pathlib`, `dataclasses`, `json`, `csv`, `hashlib`, and other standard-library modules for core operations. Do not add an ORM unless there is a clear need.

Pin dependency ranges and provide a lock file or reproducible installation instructions. Do not assume a CLI flag exists merely because it appears in an example; verify supported flags against the installed CLI's `--help` and current official documentation.

## 4. User experience and CLI

The installed command is `codebench`.

Required commands:

```text
codebench doctor
codebench tasks list [--suite NAME]
codebench tasks validate [TASK_ID]
codebench run --task TASK_ID [--agents all|claude|antigravity] [--repeat N]
codebench run --suite SUITE [--agents all|claude|antigravity] [--repeat N]
codebench runs list [--limit N]
codebench compare [--experiment ID|--latest]
codebench report [--experiment ID|--latest] [--format html]
codebench export [--experiment ID|--latest] [--format json|csv]
```

Exact syntax may be adjusted for consistency, but equivalent functionality is mandatory. CLI help and errors must be clear.

### 4.1 `doctor`

Check and report independently:

- Python version.
- Git availability/version.
- Docker availability and whether a test container can run.
- Claude CLI executable, version, authentication readiness if safely detectable, and non-destructive command/help support.
- `agy` executable, version, authentication readiness if safely detectable, and non-destructive command/help support.
- Config validity and writable data directory.
- Whether required container images can be built/pulled.
- Whether agent adapters support the configured output format and model-selection flags.

Do not send paid or state-changing tasks as part of `doctor`. A tiny opt-in smoke test may be provided separately.

### 4.2 Task commands

`tasks list` prints task ID, title, category, repository, and validation state. `tasks validate` checks metadata, source repository access, commit existence, Docker build configuration, test paths, timeout/resource settings, and test harness configuration. Validation must not run an agent.

### 4.3 Run commands

- Validate all inputs before starting an experiment.
- Default to sequential runs, not parallel.
- Use fresh workspaces for every task/agent/repetition.
- Randomize agent order per paired task/repetition using a recorded random seed.
- `--repeat` must be a positive integer; default 1.
- Record configuration snapshot and hashes at experiment start.
- If an agent is not available, fail early or skip it only when the user explicitly requested a partial run. Never silently label an incomplete experiment as a full comparison.
- Provide progress updates without dumping secrets.
- Ctrl+C must terminate the active process/container, mark the run `interrupted`, save available artifacts, and exit cleanly.
- Do not automatically rerun failed attempts.

## 5. Repository layout

Use a standard `src` layout:

```text
codebench-local/
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── config/
│   └── benchmark.toml
├── tasks/
│   ├── pilot/
│   │   └── example-task/
│   │       ├── task.toml
│   │       ├── instruction.md
│   │       ├── environment/
│   │       │   └── Dockerfile
│   │       ├── evaluator/
│   │       │   ├── run_tests.sh
│   │       │   └── tests/
│   │       └── solution/
│   │           └── README.md
├── src/
│   └── codebench/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── models.py
│       ├── doctor.py
│       ├── task_registry.py
│       ├── scheduler.py
│       ├── workspace.py
│       ├── docker_runner.py
│       ├── evaluator.py
│       ├── scoring.py
│       ├── storage.py
│       ├── reporting.py
│       ├── export.py
│       ├── redaction.py
│       └── agents/
│           ├── __init__.py
│           ├── base.py
│           ├── claude_code.py
│           └── antigravity.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── runs/  # generated, gitignored
```

Implementation may reorganize modules if separation of concerns remains clear. Do not commit real run artifacts, credentials, provider session data, or private task repositories.

## 6. Configuration

Provide `config/benchmark.toml` with documented defaults. Example:

```toml
[data]
directory = "runs"
database = "runs/codebench.sqlite3"
artifact_retention = "all"

[execution]
default_timeout_seconds = 900
startup_grace_seconds = 10
parallelism = 1
network_enabled_for_agent = false
cpu_limit = 2
memory_limit = "4g"
pids_limit = 256
container_user = "10001:10001"
workspace_cleanup = "retain"
random_seed = 20261010

[agents.claude]
enabled = true
command = "claude"
model = "" # empty means CLI/provider default; record as unresolved if exact model is unavailable
timeout_seconds = 900
output_format = "json" # adapter must verify support and may choose a documented equivalent

[agents.antigravity]
enabled = true
command = "agy"
model = "" # empty means CLI/provider default; record as unresolved if exact model is unavailable
timeout_seconds = 900
output_format = "stream-json" # use only if supported by installed CLI version

[report]
title = "CodeBench Local"
include_full_logs = false
```

Do not silently accept invalid values. Config may be overridden by CLI flags, and the resolved configuration must be recorded for every experiment. Do not write credentials to config or SQLite.

A user can override resource limits per task. A task timeout must never exceed a configured global maximum unless an explicit override flag is supplied and logged.

## 7. Task format

Each task is a directory under `tasks/<suite>/<task-id>/`.

### 7.1 `task.toml` schema

Example:

```toml
schema_version = 1
id = "example-task"
title = "Fix an edge case in a parser"
category = "bugfix"
suite = "pilot"
description = "A representative repository-level bug-fix task."
repository = "https://example.invalid/owner/repo.git"
commit = "0123456789abcdef0123456789abcdef01234567"
instruction_file = "instruction.md"
dockerfile = "environment/Dockerfile"
evaluator_command = ["bash", "/evaluator/run_tests.sh"]
timeout_seconds = 900
max_test_seconds = 300
cpu_limit = 2
memory_limit = "4g"
pids_limit = 256
network_enabled_for_agent = false
tags = ["python", "bugfix"]

[environment]
working_directory = "/workspace"
setup_command = ["bash", "-lc", "python -m pip install -e '.[test]'"]

[scoring]
acceptance_weight = 1.0
build_required = true
lint_required = false
typecheck_required = false
```

The repository URL and commit above are placeholders and MUST NOT be shipped as a real benchmark task. Include a small self-contained demo fixture with a local Git repository generated by test/setup code, or document how to create a real task. The shipped example must actually run end-to-end in CI where Docker is available.

Validate paths against directory traversal and symlink escapes. Resolve task-relative paths and verify that they remain inside the task directory.

### 7.2 Task instruction

`instruction.md` contains only the prompt sent to the agent. It must not contain hidden tests, expected patch, or evaluator hints that reveal hidden assertions. The same bytes must be sent to both agents; record the instruction SHA-256.

The prompt wrapper may add a small fixed preamble that explains how to run visible tests and where the repository is located. This wrapper must be identical for all agents, versioned, and included in the experiment metadata.

### 7.3 Repository pinning

Every task must pin a full Git commit hash, not a branch or mutable tag. Before each run:

1. Fetch/clone or use a safely cached bare repository.
2. Check out the exact commit in a new workspace.
3. Confirm the checked-out commit hash.
4. Ensure the workspace has no pre-existing modifications.
5. Record the starting commit and relevant dependency/image digests.

Do not share a writable checkout between agents or repetitions. A read-only object cache is allowed.

## 8. Agent adapter contract

Implement a common `AgentAdapter` interface. Suggested result fields:

```python
@dataclass
class RunResult:
    agent_name: str
    requested_model: str | None
    reported_model: str | None
    cli_version: str | None
    status: str
    exit_code: int | None
    started_at: str
    ended_at: str
    elapsed_seconds: float
    response_text: str
    stdout_path: str
    stderr_path: str
    events_path: str | None
    usage: dict
    error_category: str | None
    error_message: str | None
```

Status values must be enumerated and documented, for example:

- `completed`
- `agent_error`
- `timeout`
- `interrupted`
- `setup_error`
- `evaluation_error`
- `cancelled`

Keep agent process outcome separate from evaluator outcome. A process that exits zero but fails hidden tests is an agent execution completion and an evaluation failure, not an adapter failure.

### 8.1 Common behavior

Adapters must:

- Run as subprocesses with an argument list, never a shell-interpolated command.
- Set the task workspace as the working directory.
- Pass the task prompt safely; avoid shell quoting or command injection.
- Capture stdout and stderr to files while streaming bounded progress to the terminal.
- Apply timeouts and terminate the process group/container on timeout.
- Avoid logging environment variables or secrets.
- Preserve raw machine-readable output and parsed fields.
- Parse structured output defensively; malformed or unknown events must not crash the entire experiment.
- Record requested and reported model separately.
- Record CLI version and relevant flags.
- Record usage fields only when actually returned by the CLI/provider.
- Return `unknown`/`null` when a model or cost cannot be verified.
- Never retry automatically.

### 8.2 Claude Code adapter

Use Claude Code's documented non-interactive/print mode and a supported structured output format where available. Before implementing, inspect the installed CLI's `--help` and current official documentation. Pin the selected model using a documented model-selection flag only if configured; otherwise record that the provider default was used. Do not assume that a particular JSON field, token count, or cost field exists across all versions.

Authentication should reuse the user's existing supported CLI login without copying credentials into the application. Do not enable permission bypass or unrestricted execution flags by default. Use the container boundary as the primary isolation layer and configure tool permissions conservatively.

If the CLI cannot operate in a container with the available authentication mechanism, report that limitation clearly. Do not fall back to running an unrestricted agent on the host.

### 8.3 Antigravity adapter

Use the installed Google Antigravity CLI (`agy`) non-interactive/print mode when supported. Inspect `agy --help` and the installed version before choosing flags. Prefer documented JSON or streaming JSON output if supported; capture the raw event stream and parse recognized result, completion, usage, and error events.

Example command shape only; verify the installed CLI's current flag names and values before use:

```bash
agy -p "<task prompt>" --output-format stream-json --print-timeout 15m
```

Do not concatenate task text into a shell command. Use subprocess argument arrays and the CLI's documented prompt argument mechanism. Use documented model selection only when available. If model selection cannot be pinned or verified, record the model as provider-default/unknown and state that the experiment is a CLI configuration comparison rather than a controlled model comparison.

### 8.4 Adapter capability declaration

Each adapter should expose a capability record indicating whether it supports:

- non-interactive task execution,
- model selection,
- structured output,
- reported model identity,
- usage/token telemetry,
- provider-reported cost,
- timeout enforcement,
- cancellation.

Reports must show unavailable capabilities rather than pretending parity.

## 9. Isolation and execution model

Security and test validity are release-blocking.

### 9.1 Container phases

Use separate container invocations for:

1. **Agent phase:** agent can modify only the workspace and its temporary files.
2. **Evaluation phase:** evaluator gets a read-only source snapshot plus its private test directory and writes only to an output directory.

Never mount the host's Docker socket inside the agent container. Do not mount the user's home directory or provider credential directories wholesale. Never mount hidden tests, evaluator scripts, or reference solutions into the agent phase.

If a provider CLI requires authentication files, mount only the minimum necessary credential material read-only where possible, document the exposure, and do not copy it into artifacts. If this cannot be achieved safely, the adapter must refuse the run and explain the requirement.

### 9.2 Network

Default network access is disabled during the agent phase. Build images and fetch dependencies before execution. If a task genuinely needs network access, require an explicit per-task opt-in and record it; network-enabled tasks should be reported separately because their environment is less controlled.

### 9.3 Container hardening

Apply, where supported:

- CPU, memory and PID limits.
- Non-root user.
- Read-only root filesystem except designated writable mounts.
- Dropped Linux capabilities.
- `no-new-privileges`.
- No privileged mode.
- No Docker socket.
- Explicit workspace and temporary directory mounts.
- Process-group/container termination on timeout.
- Cleanup of containers after normal completion, errors, timeout, and Ctrl+C.

The evaluator must not trust agent-produced scripts or results. The test command is defined by the trusted task configuration and run in the evaluator container.

### 9.4 Evaluator isolation and integrity

The agent must not be able to change acceptance tests, evaluator scripts, scoring rules, task metadata, or report generation. Store evaluator files outside the writable workspace and mount them read-only only in the evaluator container.

Copy the agent's resulting repository snapshot or diff into a new evaluator workspace. Use a fresh container with no provider credentials. Capture test exit status, stdout, stderr, test count, passed/failed count if machine-readable output is available, and the exact evaluator image/task hash.

The agent's self-reported test results are informational only; only the trusted evaluator determines acceptance.

### 9.5 Workspace cleanup

Default `workspace_cleanup = "retain"` for MVP so failures are inspectable, but retained workspaces must live under the application data directory and be subject to configured artifact retention. Provide `codebench runs clean` only if it has a dry-run or confirmation safeguard. Never delete user source repositories or arbitrary paths.

## 10. Experiment scheduler

An experiment consists of one task suite, a set of agents, a repeat count, and a resolved configuration snapshot.

- Default execution is sequential.
- For each task/repetition, randomize agent order using a recorded seed.
- Every agent gets its own fresh workspace.
- Paired task identity, prompt hash, starting commit, environment image, and evaluator version must match.
- If an agent fails setup, preserve the result and continue only according to documented policy. The experiment must still report incomplete pair counts.
- Do not replace failed attempts with successful retries in the headline score.
- Use a unique immutable experiment ID and unique run ID.
- Store start/end timestamps in UTC ISO 8601.
- Record host OS, architecture, Python version, Docker version, agent CLI versions, and relevant resource settings.
- Detect configuration drift during a run if practical and record it.

For fair timing, define `elapsed_seconds` as the wall-clock interval from agent process start to process completion/timeout. Report setup and evaluator time separately. Do not include image build time in agent runtime; report it separately if measured.

## 11. Evaluation and task validity

### 11.1 Acceptance outcome

Each task must define a deterministic acceptance command. Its exit code is authoritative:

- `pass`: acceptance command returns 0.
- `fail`: command returns non-zero after executing.
- `evaluation_error`: test harness could not execute reliably.
- `not_evaluated`: agent/setup did not produce a usable workspace.

Do not count `evaluation_error` as an agent failure in the main correctness denominator; report it separately and invalidate/re-run the task evaluation only under a documented administrative procedure, never by silently changing results.

### 11.2 Test result fields

Capture at least:

- evaluator status,
- exit code,
- duration,
- output paths,
- tests passed/failed/skipped if available,
- build result,
- lint result if configured,
- type-check result if configured,
- regression result,
- evaluator image digest,
- evaluator/test harness hash.

A task's main acceptance test is mandatory. Optional quality gates should be separately visible. If the task requires build, lint or type checking for acceptance, the rule must be fixed in the task definition before any run.

### 11.3 Task validation

Provide a task-validation command that checks:

- full commit hash exists,
- task files are valid and paths are safe,
- Dockerfile builds,
- evaluator command is present,
- reference solution passes acceptance tests,
- original starting commit fails the intended acceptance test (where the task is designed to require a code change),
- hidden tests are not mounted into the agent workspace,
- task prompt and metadata hashes can be recorded.

A task is not eligible for scored runs until validation passes. Provide an explicit administrative override only if needed for debugging; overridden runs must be marked unvalidated and excluded from the headline score.

### 11.4 Demo task

Ship at least one small, real, self-contained demo task using a tiny repository created locally by setup/test code, not a fake external URL. It must have:

- a reproducible Git commit,
- a clear bug or small feature,
- a visible README/test command,
- hidden acceptance test(s),
- a reference solution that passes,
- original commit that fails the intended test,
- a Docker environment that can be built offline after dependencies are available.

If a complete offline image is impractical, clearly document the one-time dependency download step and pin dependency versions.

## 12. Metrics and scoring

Do not collapse everything into an opaque single number. Present the following primary metrics:

### 12.1 Correctness

- `eligible_evaluations`: completed, valid evaluations for which the task/agent attempt is eligible.
- `acceptance_passes`: attempts whose acceptance tests pass.
- `pass_rate = acceptance_passes / eligible_evaluations`.
- `task_solved_rate`: fraction of task/repetition pairs where an agent passes.
- `paired_win_rate`: fraction of valid paired comparisons where only one agent passes; show ties separately.
- `timeout_rate`, `agent_error_rate`, `setup_error_rate`, `evaluation_error_rate`.

Never count invalid tasks, evaluation errors, or missing runs as ordinary acceptance failures. Show denominators for every rate.

### 12.2 Runtime

For successful runs, report median and interquartile range of agent wall-clock time. Also report runtime for all completed attempts and timeout count. Avoid averaging timeouts as if they had known completion times; optionally show capped elapsed time separately with the cap explicitly stated.

### 12.3 Cost and usage

- Record provider-reported cost if present.
- Record input/output/cache token counts only if supplied and semantics are known.
- Store raw usage payload for audit, with secrets removed.
- `cost_per_success` = total known cost for all attempts in a clearly defined cohort divided by number of successful attempts in that cohort.
- If any cost is unknown, report coverage and do not present the known-cost subset as the total cost without labeling it.
- For subscription plans with no per-run cost telemetry, display `not available` or a user-entered estimate clearly labeled as such. Do not invent an allocation.

### 12.4 Quality gates

Report acceptance, build, lint, type-check, regression, and optional security outcomes separately. Do not grade source-code similarity to a reference patch: alternative valid implementations are allowed.

### 12.5 Statistical caution

Show raw per-task outcomes and sample counts. For pass-rate differences, optionally report a paired bootstrap confidence interval if implemented and tested; it is not required for the first release. Do not call a small pilot statistically conclusive. Do not declare a winner from tiny differences without showing uncertainty and task-level results.

## 13. Storage schema

Use SQLite with schema versioning and transactions. Minimum logical tables:

### `experiments`

- `id` primary key
- `created_at`
- `started_at`, `ended_at`
- `status`
- `suite`
- `task_ids_json`
- `agent_names_json`
- `repeat_count`
- `random_seed`
- `resolved_config_json`
- `host_info_json`
- `tool_versions_json`
- `notes`

### `runs`

- `id` primary key
- `experiment_id` foreign key
- `task_id`
- `agent_name`
- `repetition`
- `pair_key`
- `order_index`
- `status`
- `requested_model`
- `reported_model`
- `cli_version`
- `starting_commit`
- `instruction_sha256`
- `environment_digest`
- `evaluator_digest`
- `started_at`, `ended_at`
- `elapsed_seconds`
- `exit_code`
- `error_category`, `error_message`
- `usage_json`
- `artifact_dir`

### `evaluations`

- `id` primary key
- `run_id` foreign key
- `status`
- `acceptance_pass`
- `exit_code`
- `duration_seconds`
- `tests_passed`, `tests_failed`, `tests_skipped`
- `build_pass`
- `lint_pass`
- `typecheck_pass`
- `regression_pass`
- `output_json`
- `evaluator_version`

### `artifacts`

- `id` primary key
- `run_id` foreign key
- `kind`
- `relative_path`
- `sha256`
- `size_bytes`
- `redacted`
- `created_at`

Enforce foreign keys and use transactions. Use migrations or a `schema_version` table. Never store credentials, access tokens, or full environment dumps. Database records must not assume all usage fields exist.

## 14. Artifact policy and privacy

Per-run artifact directory should include as appropriate:

```text
runs/<experiment-id>/<run-id>/
├── metadata.json
├── prompt.txt
├── stdout.log
├── stderr.log
├── events.jsonl
├── agent-result.json
├── diff.patch
├── git-status.txt
├── evaluator/
│   ├── result.json
│   ├── stdout.log
│   └── stderr.log
└── workspace/             # optional retained copy
```

Artifact names may vary, but paths and hashes must be stored. Do not save secrets or full environment variables. Redact common token/credential patterns from logs, but do not claim perfect redaction. Provide a configurable artifact-retention policy. Never publish or upload artifacts automatically.

Prompts may contain proprietary source context; treat all run artifacts as private local data.

## 15. Reporting

Generate a static HTML report using local data only; no external analytics, tracking, or remote assets. Escape all task names, prompts, logs, and output before rendering HTML to prevent injection.

Required report sections:

1. Experiment metadata and resolved configuration.
2. Agent versions and model identity confidence.
3. Overall pass rate with numerators and denominators.
4. Paired task outcomes: A wins, B wins, both pass, neither passes, invalid pair.
5. Per-category pass rates.
6. Median successful runtime and IQR.
7. Timeout/error rates.
8. Cost/usage with data-coverage warnings.
9. Quality-gate results.
10. Per-task comparison with links to local artifact files.
11. Failures grouped by category.
12. Clear warning if the experiment is incomplete, task validity is compromised, model identity is unknown, or telemetry is not comparable.

Provide JSON export of raw records and CSV export of a flattened per-run summary. Exports must be deterministic and include schema/version metadata where practical.

## 16. CLI exit codes and errors

Use stable non-zero exit codes for invalid config/task, missing dependency, failed setup, and interrupted experiment where practical. Document them.

- A benchmark run can finish successfully as an experiment even if some agents fail; distinguish experiment execution status from coding-task success.
- Invalid task configuration must fail before launching any agent.
- Agent non-zero exit is a recorded result, not necessarily a CLI crash.
- Evaluator infrastructure failure must be clearly distinguished from a rejected solution.
- Error messages must explain the next corrective action without exposing credentials.
- Do not print full prompts or source code unless explicitly requested.

## 17. Test plan

### 17.1 Unit tests

- Config parsing, defaults, overrides, invalid values.
- Task schema and path traversal rejection.
- Prompt wrapper identity and SHA-256.
- Run status transitions.
- Timeout and interruption handling.
- Randomized ordering reproducibility with a fixed seed.
- Paired-run matching and missing-pair handling.
- Scoring formulas and denominators.
- Usage normalization with missing/unknown fields.
- Cost coverage calculations.
- HTML escaping and log redaction.
- SQLite schema migrations and transaction integrity.
- CSV/JSON export determinism.

### 17.2 Adapter tests

Use fake executables in tests; do not require paid provider calls.

- Successful completion.
- Non-zero exit.
- Timeout.
- malformed JSON/JSONL.
- missing model/usage fields.
- unsupported flags.
- stdout/stderr separation.
- prompt containing quotes, Unicode, newlines, shell metacharacters.
- Ctrl+C/termination behavior.

### 17.3 Integration tests

- Demo task validates.
- Fake agent can make a passing patch.
- Fake agent can make a failing patch.
- Evaluator detects both outcomes.
- Agent cannot read or alter hidden tests.
- Each attempt starts from the pinned commit.
- Runs persist after an interruption.
- Full experiment creates HTML, JSON and CSV reports.
- Docker cleanup occurs after success and failure.

A small optional manual smoke-test procedure should validate real CLIs without being part of routine automated CI. CI must not require user credentials or spend provider credits.

## 18. Acceptance criteria for v0.1

The implementation is accepted only when all applicable criteria pass:

1. A clean install provides a working `codebench --help`.
2. `codebench doctor` reports missing dependencies accurately and does not start a paid coding task.
3. The shipped demo task validates end to end.
4. A single command can run both adapters on the same task when both CLIs are installed and authenticated.
5. Every run uses a fresh workspace pinned to the same commit for its paired comparison.
6. The agent cannot modify or access evaluator tests/scripts through the configured mounts.
7. Timeouts and Ctrl+C terminate the active execution safely and preserve results.
8. A non-zero agent exit, timeout, test failure, and evaluator infrastructure failure are distinguishable.
9. Missing model identity, token telemetry, or cost data is explicitly represented as unknown/unavailable.
10. Repeated trials are scheduled with reproducible randomized order using a stored seed.
11. SQLite persists experiments, runs, evaluations, and artifact references.
12. HTML, JSON, and CSV outputs can be generated from a completed experiment.
13. Reports show denominators, invalid evaluations, missing pairs, and incomplete experiments.
14. Tests run without real provider credentials or paid API calls by using fake adapters.
15. Documentation covers setup, authentication assumptions, task creation, security, known limitations, and result interpretation.
16. Lint and unit tests pass.
17. No secrets, provider tokens, or private generated run artifacts are committed.
18. No fake claim of model-level isolation is made when comparing full CLI systems.

## 19. Implementation plan

Implement in this order:

### Milestone 1 — Core runner and demo task
- Package and CLI skeleton.
- Task schema and validation.
- Git workspace management.
- Docker execution and trusted evaluator.
- Fake agent for integration testing.
- Demonstrate one pass and one failure.

### Milestone 2 — Provider adapters
- Claude Code adapter.
- Antigravity adapter.
- Version/capability detection.
- Structured output parsing and robust timeouts.
- Manual smoke test instructions.

### Milestone 3 — Experiments and persistence
- SQLite schema.
- Paired randomized scheduler.
- Repeats and interruption handling.
- Artifact hashes and retention.

### Milestone 4 — Metrics and reports
- Scoring and paired comparisons.
- HTML, JSON and CSV reports.
- Failure categorization and telemetry coverage.
- End-to-end integration tests.

### Milestone 5 — Pilot suite
- Add and validate 24 representative tasks, preferably from the user's own repositories.
- Run three repetitions per agent.
- Review invalid tasks, failure modes, and whether the results match real-world experience.
- Do not publish or treat the pilot as statistically conclusive.

## 20. Implementation instructions for the coding agent

Treat this specification as the source of truth. Before coding:

1. Inspect the target repository and report its current state; preserve useful existing work.
2. Verify current official documentation and installed `claude` and `agy` CLI help for exact command flags and output formats. Do not guess CLI behavior.
3. Write a short implementation plan mapped to the milestones and identify any CLI capability that cannot be verified.
4. Implement the complete v0.1 scope, not just a skeleton or pseudocode.
5. Do not silently weaken security requirements to make a demo pass. If safe credential access in containers is not feasible, document the blocker and implement a clear, fail-closed diagnostic.
6. Add tests alongside implementation. Tests must not need paid model calls.
7. Run lint, unit tests, and Docker integration tests where Docker is available.
8. Exercise the demo end to end using fake agents, then validate real adapters non-destructively.
9. Review the diff for secrets, shell injection, path traversal, hidden-test exposure, unsafe mounts, swallowed errors, and unbounded processes.
10. Update README with actual commands that work in the implementation. Do not document unsupported flags or claim untested OS support.
11. Report completed features, tests actually run, known limitations, and exact commands for a first local run. Never claim tests passed unless they were executed.

If a requirement cannot be implemented safely or verified from documentation, state the exact blocker and propose the smallest safe alternative. Do not fabricate test results, benchmark scores, provider capabilities, or pricing.

## 21. Definition of done

v0.1 is done when a developer can clone/install the project, run the demo task with fake agents, validate a real task, execute paired Claude Code and Antigravity CLI attempts in isolated environments, independently grade their results, inspect artifacts, and generate a report that transparently communicates correctness, speed, cost-data coverage, uncertainty, and limitations.

**Primary success criterion:** The tool produces an honest, repeatable comparison of real coding-task outcomes—not merely a leaderboard of model names or generated text.
