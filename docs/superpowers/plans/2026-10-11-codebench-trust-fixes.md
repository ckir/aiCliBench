# CodeBench Trust Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CodeBench's scores trustworthy (verified task oracles, enforced quality gates, uncertainty on paired results, reproducible task repos, experiment provenance) and make the harness agent-neutral (generic CLI adapter, task scaffold).

**Architecture:** All domain logic lands in `ai_benchmark` (new modules `task_materialize`, `task_verify`, `task_scaffold`, `provenance`; extended `evaluator`, `scoring`, `storage`, `scheduler`, `reporting`). Contracts change only in `ai_schemas.codebench`. The CLI (`ai_cli.codebench`) gains four `tasks` subcommands and wider `--agents`. One new workspace package, `ai-integration-generic-cli`, implements the existing `AgentAdapter` protocol.

**Tech Stack:** Python 3.12+, Pydantic v2, Typer, stdlib (`subprocess`, `sqlite3`, `hashlib`, `random`, `math`), Jinja2, pytest, uv workspace, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-10-11-codebench-trust-fixes-design.md` (sections D1–D8 plus "Builder-check decisions" 1–9).

## Global Constraints

- Dependencies flow inward; `ai_schemas` imports no integration or benchmark code; no network or subprocess at import time.
- Public functions typed; `dataclass(frozen=True, slots=True)` for internal values; Pydantic v2 `model_config = {"extra": "forbid"}` for external data; exceptions are `ConfigurationError` / `ValidationError` from `ai_core.errors`, re-raised with `from exc`.
- Subprocess calls use argv lists, never shell strings; `# noqa: S603`/`S607` comments as in existing code.
- Gate (run from repo root): `uv run ruff check . && uv run ruff format --check . && uv run ty check --exclude "tasks/**/tests/*.py" --exclude "tasks/**/source/*.py" --exclude "tasks/**/evaluator/**/*.py" && uv run pytest --import-mode=importlib -q`. Expected tail: `N passed, 1 skipped` (the skip is `test_openai.py:137`, OPENAI_API_KEY unset). Baseline before this plan: 142 passed.
- Conventional Commits with the attribution trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Fixed git identity for task repos: name `CodeBench Demo`, email `demo@example.invalid`, author and committer date `2026-01-01T00:00:00Z`, commit message `initial: <task-id>`.
- `tasks/**/repo/` stays gitignored; never commit a generated repo. Never commit `.codebench/`.

## Review Focus

1. A task whose `solution/files/` fixes the bug but whose hidden test is wrong (passes on the original) must be reported as a broken oracle, not as a valid task → Task 8 `test_verify_detects_original_passing`.
2. A required gate that passes while the acceptance test fails must not turn the evaluation into a pass → Task 2 `test_gate_pass_does_not_rescue_failed_acceptance`.
3. A custom agent named `claude` or with an invalid name must be rejected at config load, before any run → Task 6 `test_custom_agent_name_rules`.
4. An experiment database created at schema v1 must open under v2 with the new column and no data loss → Task 9 `test_migrate_v1_to_v2_preserves_rows`.
5. Materializing a task whose `repo/` was hand-edited must refuse silently reusing it → Task 5 `test_materialize_dirty_repo_rejected`.

---

### Task 1: TaskScoring gates in the schema

**Files:**
- Modify: `packages/schemas/src/ai_schemas/codebench.py:120-126` (`TaskScoring`)
- Test: `packages/schemas/tests/test_codebench.py`

**Interfaces:**
- Produces: `TaskScoring(acceptance_weight: float = 1.0, build_required: bool = False, lint_required: bool = False, typecheck_required: bool = False, build_command: list[str] = [], lint_command: list[str] = [], typecheck_command: list[str] = [])` with a `model_validator(mode="after")` raising `ValueError("<gate>_required needs <gate>_command")`.

- [ ] **Step 1: Write the failing tests** in `packages/schemas/tests/test_codebench.py`:

```python
def test_task_scoring_gate_defaults_and_required_needs_command():
    scoring = TaskScoring()
    assert scoring.build_required is False
    assert scoring.build_command == []
    with pytest.raises(ValidationError):  # pydantic.ValidationError
        TaskScoring(lint_required=True)
    ok = TaskScoring(typecheck_required=True, typecheck_command=["python3", "-m", "mypy", "."])
    assert ok.typecheck_required is True
```

- [ ] **Step 2: Run** `uv run pytest packages/schemas/tests/test_codebench.py -q` → FAIL (`build_required` is `True`, no `build_command`).
- [ ] **Step 3: Implement** the fields and validator in `TaskScoring` (spec D4). Keep `model_config = {"extra": "forbid"}`.
- [ ] **Step 4: Run** the schemas tests → PASS. Run `uv run pytest packages/benchmark -q` → still PASS (no pilot task sets a gate yet).
- [ ] **Step 5: Commit** `feat(schemas): opt-in quality gate commands on TaskScoring`.

### Task 2: Evaluator runs configured gates

**Files:**
- Modify: `packages/benchmark/src/ai_benchmark/evaluator.py` (`EvaluatorResult` at :24-34; `run_evaluation` at :61-183)
- Test: `packages/benchmark/tests/test_evaluator.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True, slots=True) class GateSpec: build: tuple[str, ...] = (); lint: tuple[str, ...] = (); typecheck: tuple[str, ...] = (); build_required: bool = False; lint_required: bool = False; typecheck_required: bool = False` with `@classmethod from_scoring(cls, scoring: TaskScoring, *, resolve: Callable[[list[str]], list[str]] | None = None) -> GateSpec` (applies `resolve` to each non-empty command) and `def configured(self) -> dict[str, tuple[str, ...]]` returning the non-empty gates in order build, lint, typecheck.
  - `EvaluatorResult` gains trailing fields `build_pass: bool | None = None`, `lint_pass: bool | None = None`, `typecheck_pass: bool | None = None`, `gate_outputs: dict[str, str] = field(default_factory=dict)` (key = gate name, value = last 2000 chars of stdout+stderr).
  - `run_evaluation(..., gates: GateSpec | None = None)`; all other parameters unchanged.
  - Internal helper `_execute(command: list[str], *, eval_workspace: Path, evaluator_dir: Path, output_dir: Path, timeout_seconds: float, image: str, use_docker: bool, name: str) -> ContainerResult` extracted from the current docker/local branches; local mode env additionally sets `PYTHONDONTWRITEBYTECODE=1`.
- Semantics (spec D4 + decision 4): acceptance timeout → `EVALUATION_ERROR`, gates not run. Otherwise run each configured gate; any gate `timed_out` → `EVALUATION_ERROR`, `acceptance_pass=None`, gate passes recorded as `None`. Else `X_pass = (exit_code == 0)`; `acceptance_pass = acceptance_exit == 0 and all(required gate passes)`; `status = PASS if acceptance_pass else FAIL`.

- [ ] **Step 1: Write failing tests** (helpers `_make_snapshot`, `_make_evaluator` already exist; add `_gate_script(root, name, exit_code) -> list[str]` writing `root/<name>.sh` that echoes its name and exits with `exit_code`):

```python
def test_gate_required_fail_makes_evaluation_fail(tmp_path):
    snap = _make_snapshot(tmp_path / "s", "x\n")
    ev = _make_evaluator(tmp_path / "e", passes=True)
    gates = GateSpec(lint=tuple(_gate_script(tmp_path, "lint", 1)), lint_required=True)
    r = run_evaluation(
        snapshot_dir=snap,
        evaluator_dir=ev,
        evaluator_command=["bash", str(ev / "run_tests.sh")],
        output_dir=tmp_path / "o",
        timeout_seconds=30,
        use_docker=False,
        gates=gates,
    )
    assert r.status == EvalStatus.FAIL and r.acceptance_pass is False
    assert r.lint_pass is False and r.build_pass is None and "lint" in r.gate_outputs


def test_gate_optional_fail_recorded_only(
    tmp_path,
): ...  # lint not required, exit 1 → status PASS, acceptance_pass True, lint_pass False


def test_gate_pass_does_not_rescue_failed_acceptance(
    tmp_path,
): ...  # evaluator passes=False, build gate exit 0 required → FAIL, build_pass True


def test_gate_timeout_is_evaluation_error(
    tmp_path,
): ...  # gate = ["python3", "-c", "import time; time.sleep(5)"], timeout_seconds=0.3 → EVALUATION_ERROR, acceptance_pass None


def test_gate_spec_from_scoring_resolves_commands():
    spec = GateSpec.from_scoring(
        TaskScoring(build_required=True, build_command=["bash", "/evaluator/b.sh"]),
        resolve=lambda c: ["R", *c],
    )
    assert spec.build == ("R", "bash", "/evaluator/b.sh") and spec.configured() == {
        "build": spec.build
    }


def test_evaluator_digest_ignores_pycache(tmp_path):
    ev = _make_evaluator(tmp_path / "d", passes=True)
    before = evaluator_digest(ev)
    (ev / "__pycache__").mkdir()
    (ev / "__pycache__" / "x.cpython-313.pyc").write_bytes(b"\x00")
    (ev / "run_tests.pyc").write_bytes(b"\x00")
    (ev / ".pytest_cache").mkdir()
    (ev / ".pytest_cache" / "v").write_text("1")
    assert evaluator_digest(ev) == before
```

- [ ] **Step 2: Run** `uv run pytest packages/benchmark/tests/test_evaluator.py -q` → FAIL (`GateSpec` undefined).
- [ ] **Step 3: Implement** `GateSpec`, `_execute`, the gate loop, and the digest exclusion (`evaluator_digest` skips any path with a part in `{"__pycache__", ".pytest_cache"}` or suffix `.pyc`). Also add `PYTHONDONTWRITEBYTECODE=1` to the local env.
- [ ] **Step 4: Run** `uv run pytest packages/benchmark -q` → PASS.
- [ ] **Step 5: Commit** `feat(benchmark): run configured build/lint/typecheck gates in the evaluator`.

### Task 3: Scheduler persists gates; example-task gets a real gate

**Files:**
- Modify: `packages/benchmark/src/ai_benchmark/scheduler.py` (`_run_once` evaluation phase :474-540; `_resolve_eval_command` :566-579)
- Modify: `tasks/pilot/example-task/task.toml` (`[scoring]` block)
- Test: `packages/benchmark/tests/test_scheduler.py`

**Interfaces:**
- Consumes: `GateSpec.from_scoring(task.scoring, resolve=lambda c: _resolve_eval_command(c, evaluator_dir))`, `EvaluatorResult.build_pass/lint_pass/typecheck_pass/gate_outputs`.
- Produces: evaluation rows with `build_pass`, `lint_pass`, `typecheck_pass` as `1/0/None` and `output_json` carrying `"gates": {name: tail}`.

- [ ] **Step 1: Edit** `tasks/pilot/example-task/task.toml` `[scoring]`: `build_required = true`, `build_command = ["python3", "-m", "compileall", "-q", "."]` (keep the other keys).
- [ ] **Step 2: Write the failing test** in `test_scheduler.py`:

```python
def test_scheduler_records_gate_results(tmp_path):
    # reuse test_scheduler_full_experiment_with_fakes setup (fake pass + fake fail), experiment_id="exp_gates"
    conn = connect(db)
    evals = {
        r["agent_name"]: evaluation_for_run(conn, r["id"])
        for r in runs_for_experiment(conn, "exp_gates")
    }
    assert evals["claude"]["build_pass"] == 1 and evals["claude"]["acceptance_pass"] == 1
    assert evals["antigravity"]["build_pass"] == 1 and evals["antigravity"]["acceptance_pass"] == 0
    assert evals["claude"]["lint_pass"] is None
    assert "gates" in json.loads(evals["claude"]["output_json"])
```

- [ ] **Step 3: Run** `uv run pytest packages/benchmark/tests/test_scheduler.py -q` → FAIL (`build_pass` is None).
- [ ] **Step 4: Implement** in `_run_once`: build the `GateSpec`, pass `gates=` to `run_evaluation`, map the three passes to `1/0/None`, add `"gates": eval_result.gate_outputs` to `output_json`.
- [ ] **Step 5: Run** `uv run pytest packages/benchmark -q` → PASS (note: `test_demo.py` calls `run_evaluation` without gates; unchanged).
- [ ] **Step 6: Commit** `feat(benchmark): persist quality-gate outcomes per evaluation; build gate on example-task`.

### Task 4: Gate counts in scoring, report §9 and `compare`

**Files:**
- Modify: `packages/benchmark/src/ai_benchmark/scoring.py:252-256` (`gates[agent]`)
- Modify: `packages/benchmark/src/ai_benchmark/reporting.py:99-105` (section 9 template) and `render_report`
- Modify: `packages/cli/src/ai_cli/codebench.py` (`compare` output, after the cost lines)
- Test: `packages/benchmark/tests/test_scoring.py`, `packages/benchmark/tests/test_reporting.py`

**Interfaces:**
- Produces: `ScoreReport.quality_gates[agent] == {"acceptance_pass": int, "eligible": int, "build_pass": int, "build_total": int, "lint_pass": int, "lint_total": int, "typecheck_pass": int, "typecheck_total": int}` where `*_total` counts evaluations whose column is not `None` and `*_pass` counts value `1`/`True`.

- [ ] **Step 1: Failing tests**: `test_quality_gate_counts` (two runs, evals with `build_pass` 1 and 0, `lint_pass` None → `build_pass 1, build_total 2, lint_total 0`); in `test_reporting.py` extend `test_html_escapes_injection` sample eval with `"build_pass": 1` and assert `"Build"` and `"1/1"` appear in the §9 table.
- [ ] **Step 2: Run** both test files → FAIL.
- [ ] **Step 3: Implement**: scoring counts; §9 template columns `Agent | Acceptance | Build | Lint | Typecheck` rendering `pass/total` or `n/a` when total is 0; `compare` prints one line per agent: `{agent} gates: build {p}/{t}, lint {p}/{t}, typecheck {p}/{t}`.
- [ ] **Step 4: Run** `uv run pytest packages/benchmark packages/cli -q` → PASS.
- [ ] **Step 5: Commit** `feat(benchmark): report quality-gate counts separately from acceptance`.

### Task 5: Task repository materialization + repin

**Files:**
- Create: `packages/benchmark/src/ai_benchmark/task_materialize.py`
- Modify: `packages/benchmark/src/ai_benchmark/task_registry.py:125-190` (`validate_task`) — call materialization when `check_repo` and repository is task-relative
- Modify: `packages/benchmark/src/ai_benchmark/scheduler.py:255-300` (`_run_once`, before `checkout_fresh`)
- Modify: `packages/benchmark/tests/test_demo.py:14-63` (replace `_ensure_demo_repo` body with `materialize_repo(DEMO_DIR)`)
- Modify: `tasks/pilot/example-task/task.toml`, `tasks/pilot/semver-comparator/task.toml` (`commit =` line, via `--repin`)
- Modify: `packages/cli/src/ai_cli/codebench.py` (new `tasks materialize`)
- Test: `packages/benchmark/tests/test_task_materialize.py`, `packages/cli/tests/test_tasks_materialize.py`

**Interfaces:**
- Produces:
  - `FIXED_GIT_ENV: dict[str, str]` (the six `GIT_*` variables from Global Constraints).
  - `class MaterializeMismatchError(ConfigurationError)` with attributes `expected: str`, `actual: str`.
  - `@dataclass(frozen=True, slots=True) class MaterializeResult: task_id: str; repo_path: Path | None; commit: str | None; pinned_commit: str; action: Literal["kept", "generated", "skipped"]`.
  - `def materialize_repo(task_dir: Path, *, force: bool = False, check: bool = True) -> MaterializeResult`.
  - `def repin_task(task_dir: Path, commit: str) -> None` (rewrites only the line matching `^commit = ".*"$`).
  - `def generated_commit_message(task_id: str) -> str` → `f"initial: {task_id}"`.
- Behaviour: `repository` not task-relative or `source/` missing → `skipped`. `repo/` exists: HEAD == pinned and `git status --porcelain` empty → `kept`; dirty → `ConfigurationError("task repo modified: <path>; re-run with force")` unless `force`; HEAD != pinned → regenerate only if `force`, else `MaterializeMismatchError`. Generation: copy every regular file under `source/` (sorted, `symlinks=False`, skip `__pycache__`/`.pyc`) into a temp dir beside `repo/`, run `git init`, `git add -A`, `git -c commit.gpgsign=false commit -q -m <msg>` with `env={**os.environ, **FIXED_GIT_ENV}`, read `rev-parse HEAD`; if `check` and it differs from pinned → delete temp dir, raise `MaterializeMismatchError`; else atomically rename to `repo/` → `generated`.

- [ ] **Step 1: Failing tests** (`_write_source_task(tmp_path, task_id, pinned="0"*40)` builds a task dir with `source/a.py`):

```python
def test_materialize_generates_and_repins(tmp_path):
    task = _write_source_task(tmp_path, "t1")
    first = materialize_repo(task, check=False)
    assert first.action == "generated" and len(first.commit) == 40
    repin_task(task, first.commit)
    assert materialize_repo(task).action == "kept"
    shutil.rmtree(task / "repo")
    again = materialize_repo(task)
    assert again.action == "generated" and again.commit == first.commit  # deterministic

def test_materialize_mismatch_raises(tmp_path):  # pinned "0"*40 → MaterializeMismatchError with .expected == "0"*40
def test_materialize_dirty_repo_rejected(tmp_path):  # after kept, write repo/extra.txt → ConfigurationError; force=True → "generated"
def test_materialize_skips_remote_repository(tmp_path):  # repository = "https://example.invalid/r.git" → "skipped"
def test_repin_rewrites_only_commit_line(tmp_path):  # other lines byte-identical
```

CLI test: `tasks materialize t1` on a tmp root with wrong pin → exit 3 and output contains `mismatch`; with `--repin` → exit 0 and `task.toml` updated.

- [ ] **Step 2: Run** → FAIL (module missing).
- [ ] **Step 3: Implement** the module; wire `validate_task` (append the mismatch message to `errors`, dirty-repo message to `errors`), `_run_once` (materialize failure → `setup_error` path that already exists), and the CLI command `tasks materialize [TASK_ID] [--suite] [--force] [--repin]` (exit `EXIT_TASK` on mismatch without `--repin`).
- [ ] **Step 4: Repin the two outliers**: `uv run codebench tasks materialize example-task --force --repin` and the same for `semver-comparator`; confirm `git diff tasks/pilot` shows only the two `commit =` lines.
- [ ] **Step 5: Replace** `_ensure_demo_repo` in `test_demo.py` with a call to `materialize_repo(DEMO_DIR, force=True)`.
- [ ] **Step 6: Run** `uv run pytest packages/benchmark packages/cli -q` → PASS.
- [ ] **Step 7: Commit** `feat(benchmark): deterministic task repo materialization with pinned-commit check`.

### Task 6: Generic CLI adapter package and custom agents config

**Files:**
- Create: `packages/integrations/generic-cli/pyproject.toml` (name `ai-integration-generic-cli`, deps `ai-core`, `ai-schemas`, `ai-agents`, `ai-benchmark` (for `redaction`, same precedent as the sibling adapters), `pydantic>=2`; hatch wheel `src/ai_integration_generic_cli`), `README.md`, `src/ai_integration_generic_cli/__init__.py`, `config.py`, `adapter.py`, `tests/test_generic_cli.py`
- Modify: `pyproject.toml` (root deps + `[tool.uv.sources]`), `packages/cli/pyproject.toml` (dep + source), `release-please-config.json`, `.release-please-manifest.json` (`"packages/integrations/generic-cli": "0.1.0"`), `uv.lock` via `uv sync`
- Modify: `packages/schemas/src/ai_schemas/codebench.py:49-76` (`CustomAgentConfig`, `AgentsConfig.custom`, `enabled_agents`), `:85-111` (`_check_timeouts` loops custom too)
- Modify: `packages/cli/src/ai_cli/codebench.py:65-106` (`_resolve_agents`), `:133-149` (`doctor`), `run` note when >2 agents
- Modify: `packages/benchmark/src/ai_benchmark/doctor.py:126-143` (`run_doctor(..., custom_commands: dict[str, str] | None = None)` → one `_cli_check(name, cmd)` each)
- Modify: `docs/codebench-configuration.md`
- Test: `packages/schemas/tests/test_codebench.py`, `packages/cli/tests/test_codebench.py`

**Interfaces:**
- `ai_schemas.codebench.CustomAgentConfig(enabled: bool = True, command: str, args: list[str] = [], output_format: Literal["json", "jsonl", "text"] = "text", model: str = "", model_flag: str = "", version_args: list[str] = ["--version"], timeout_seconds: int = 900)`; `AgentsConfig.custom: dict[str, CustomAgentConfig] = {}` validated: key matches `^[a-z][a-z0-9_-]{0,31}$` and not in `{"claude", "antigravity"}` else `ValueError("invalid custom agent name: ...")`.
- `ai_integration_generic_cli.config.GenericCliConfig` — same fields as `CustomAgentConfig` minus `enabled`, `timeout_seconds: float = 900`.
- `ai_integration_generic_cli.adapter.GenericCliAdapter(name: str, config: GenericCliConfig)` with `agent_name`, `capability` (non_interactive=True, structured_output = output_format != "text", model_selection = bool(model_flag), usage_telemetry = output_format != "text", reported_cost=False), `version()` (runs `[command, *version_args]`, first line, None on failure), `check()`, `build_argv(prompt) -> list[str]` (substitute `{prompt}` tokens in `args`; if none present append prompt; append `[model_flag, model]` when both set), `run(...) -> RunResult` mirroring `ClaudeCodeAdapter.run` control flow (missing CLI → SETUP_ERROR, timeout → TIMEOUT, OSError → SETUP_ERROR, else `categorize_exit`).
- Parsing in `adapter.py`: `parse_output(stdout: str, fmt: str) -> tuple[str, str | None, UsageRecord]`; `json` → single object; `jsonl` → last parseable object that has any of `result|content|text|model|usage`; keys read: `result`/`content`/`text` for response, `model`/`model_name`, `usage{input_tokens,output_tokens,cache_tokens,total_tokens,cost_usd}` (ints ≥0 only); `text` → `(stdout[:8000], None, UsageRecord())`.
- CLI `_resolve_agents(selection, cfg)`: split on `,`; `all` → `cfg.agents.enabled_agents()`; each name must be a built-in or a custom key else exit `EXIT_CONFIG` with `Unknown --agents 'x'; use all|claude|antigravity|<custom name>`; custom → `GenericCliAdapter(name, GenericCliConfig(**fields))`.

- [ ] **Step 1: Failing tests** — adapter tests modelled on `packages/integrations/claude-code/tests/test_claude.py` (`_fake_cli`): `test_json_output_parsed`, `test_jsonl_last_object_wins`, `test_text_mode_raw`, `test_prompt_placeholder_substituted` (args `["--ask", "{prompt}", "--quiet"]`, fake CLI writes `$2` to a file → equals tricky prompt), `test_prompt_appended_when_no_placeholder`, `test_model_flag_appended`, `test_timeout_and_missing_cli`. Schema: `test_custom_agent_name_rules` (`custom={"claude": ...}` and `custom={"Bad Name": ...}` raise; `enabled_agents()` lists `codex` when enabled; `_check_timeouts` rejects custom timeout above global max). CLI: `test_resolve_agents_custom_and_list` using a `benchmark.toml` with `[agents.custom.codex] command="codex"` and `--agents claude,codex` (patch `shutil.which` not needed: construction does not probe).
- [ ] **Step 2: Run** → FAIL (package missing).
- [ ] **Step 3: Implement** package, schema, CLI, doctor wiring, release config, docs section `[agents.custom.<name>]`. Run `uv sync` to update `uv.lock`.
- [ ] **Step 4: Run** `uv run pytest packages/integrations/generic-cli packages/schemas packages/cli -q` → PASS; `uv run ty check packages/integrations/generic-cli` → `All checks passed!`.
- [ ] **Step 5: Commit** `feat(integrations): generic CLI agent adapter configurable via [agents.custom.<name>]`.

### Task 7: Statistical confidence in scoring, compare and report

**Files:**
- Modify: `packages/benchmark/src/ai_benchmark/scoring.py` (`CorrectnessSummary` :12-19, `PairedSummary` :23-30, `correctness_for_agent` :68-107, `paired_summary` :110-158)
- Modify: `packages/benchmark/src/ai_benchmark/reporting.py` (§3 :45-51, §4 :53-56, `render_report`)
- Modify: `packages/cli/src/ai_cli/codebench.py` (`compare`)
- Test: `packages/benchmark/tests/test_scoring.py`, `packages/benchmark/tests/test_reporting.py`

**Interfaces:**
- `wilson_interval(successes: int, n: int, *, z: float = 1.959964) -> tuple[float, float] | None`
- `sign_test_p_value(a_wins: int, b_wins: int) -> float | None` — `None` if both 0; else `min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)` with `n = a + b`, `k = min(a, b)`.
- `paired_bootstrap_delta_ci(outcomes: Sequence[tuple[bool, bool]], *, resamples: int = 2000, seed: int = 20261010) -> tuple[float, float] | None` — `None` if empty; resample with replacement using `random.Random(seed)`, statistic `mean(a) - mean(b)`, return 2.5th/97.5th percentiles via `_quantile_sorted`.
- `CorrectnessSummary.pass_rate_ci95: tuple[float, float] | None`; `PairedSummary.decisive_pairs: int`, `.sign_test_p_value: float | None`, `.delta_ci95: tuple[float, float] | None`, `.agent_a: str`, `.agent_b: str`.
- Valid pairs for bootstrap = pairs counted in `a_wins + b_wins + both + neither`.

- [ ] **Step 1: Failing tests**:

```python
def test_wilson_known_value():
    low, high = wilson_interval(3, 4); assert low == pytest.approx(0.3006, abs=1e-3) and high == pytest.approx(0.9545, abs=1e-3)
    assert wilson_interval(0, 0) is None
def test_sign_test_values():
    assert sign_test_p_value(8, 0) == pytest.approx(0.0078125); assert sign_test_p_value(3, 2) == 1.0; assert sign_test_p_value(0, 0) is None
def test_bootstrap_deterministic_and_bounded():
    outs = [(True, False)] * 6 + [(True, True)] * 2 + [(False, True)] * 2
    ci = paired_bootstrap_delta_ci(outs); assert ci == paired_bootstrap_delta_ci(outs)
    assert -1.0 <= ci[0] <= 0.4 <= ci[1] <= 1.0
    assert paired_bootstrap_delta_ci([(True, False)] * 5) == (1.0, 1.0)
def test_paired_summary_carries_statistics():  # extend test_paired_wins_and_ties: decisive_pairs == 1, sign_test_p_value == 1.0, delta_ci95 is not None
```

Reporting: assert `"95% CI"` in §3 and `"sign test"` in §4; when decisive pairs < 10 the §4 text contains `fewer than 10 decisive pairs`.

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**; `compare` prints `{agent}: ... pass ({rate}, 95% CI {lo:.0%}–{hi:.0%})` and after the paired line `paired stats: A={a} B={b}, decisive {n}, sign-test p={p:.3f}, delta(A-B) 95% CI [{lo:+.2f}, {hi:+.2f}]`; `n/a` substitutions when `None`.
- [ ] **Step 4: Run** `uv run pytest packages/benchmark packages/cli -q` → PASS.
- [ ] **Step 5: Commit** `feat(benchmark): Wilson intervals, exact sign test and paired bootstrap for pass rates`.

### Task 8: Solution overlays and `tasks verify`

**Files:**
- Create: `packages/benchmark/src/ai_benchmark/task_verify.py`
- Create: `tasks/pilot/example-task/solution/files/calc.py` (the fixed `add`)
- Modify: `packages/benchmark/src/ai_benchmark/task_registry.py:125-190` (`validate_task`: error `source/ missing for task-relative repository`; warning `solution/files/ missing; tasks verify cannot run`)
- Modify: `packages/cli/src/ai_cli/codebench.py` (new `tasks verify`)
- Modify: `packages/benchmark/tests/test_demo.py:72-156` (second half: use `apply_solution` instead of the fake agent for the pass case; keep the fake-agent fail case)
- Test: `packages/benchmark/tests/test_task_verify.py`, `packages/cli/tests/test_tasks_verify.py`

**Interfaces:**
- `apply_solution(task_dir: Path, workspace: Path) -> list[Path]` — copies every file under `task_dir/solution/files/` to `workspace/<same relative path>` (`safe_join` on each relative path; creates parent dirs); raises `ConfigurationError` when the overlay dir is missing or empty.
- `@dataclass(frozen=True, slots=True) class TaskVerification: task_id: str; original_status: EvalStatus | None; solution_status: EvalStatus | None; ok: bool; errors: tuple[str, ...]`.
- `verify_task(task_dir: Path, *, work_dir: Path, use_docker: bool = False) -> TaskVerification` — steps: `load_task`; `materialize_repo(task_dir)` (errors → `ok=False`); `checkout_fresh(repository=resolve_repository(...), commit=..., dest=work_dir/"original", cache_dir=work_dir/"cache")`; `run_evaluation(... gates=GateSpec.from_scoring(scoring, resolve=...), timeout_seconds=float(max_test_seconds), use_docker=use_docker)`; expect `FAIL` (`PASS` → error `original commit passes the evaluator: hidden tests are not a working oracle`; `EVALUATION_ERROR` → error with stderr tail); then `checkout_fresh(... dest=work_dir/"solution")`, `apply_solution`, evaluate, expect `PASS` (else error naming the status and failed required gates). Evaluator command resolution: reuse `_resolve_eval_command` (move it from `scheduler.py` to `evaluator.py` as a public `resolve_evaluator_command(command, evaluator_dir)` and import it back in the scheduler).
- CLI `tasks verify [TASK_ID] [--suite] [--docker/--no-docker]` prints `{id}: OK (original fail, solution pass)` or `{id}: BROKEN` + indented errors; exit `EXIT_TASK` on any failure. Work dirs under `tempfile.mkdtemp(prefix="codebench-verify-")`, removed afterwards.

- [ ] **Step 1: Failing tests** — a fixture task built from a tiny `source/` (`calc.py` buggy), `evaluator/run_tests.sh` + `tests/test_hidden.py`, and `solution/files/calc.py`: `test_verify_ok`, `test_verify_detects_original_passing` (hidden test asserts something true on the stub → `ok False`, error mentions `oracle`), `test_verify_detects_solution_failing`, `test_verify_missing_overlay_is_error`, `test_apply_solution_rejects_traversal` (overlay path `../x` → `ValidationError`). CLI: `tasks verify example-task` → exit 0 and `OK`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**; add the example-task overlay; update `validate_task` and `test_demo.py`.
- [ ] **Step 4: Run** `uv run pytest packages/benchmark packages/cli -q` → PASS; `uv run codebench tasks verify example-task` → `example-task: OK`.
- [ ] **Step 5: Commit** `feat(benchmark): tasks verify proves original fails and reference solution passes`.

### Task 9: Provenance manifest, environment digest, image cache, schema v2

**Files:**
- Create: `packages/benchmark/src/ai_benchmark/provenance.py`
- Modify: `packages/benchmark/src/ai_benchmark/storage.py:12` (`SCHEMA_VERSION = 2`), `:36` (`provenance_json TEXT NOT NULL DEFAULT '{}'` after `notes`), `:96-114` (`connect` migrations), `:149-161` (`insert_experiment` includes `:provenance_json` with default `'{}'` when absent), new `update_experiment_provenance(conn, experiment_id, provenance_json: str)`
- Modify: `packages/schemas/src/ai_schemas/codebench.py:206-222` (`ExperimentRecord.provenance: dict[str, Any] = {}`)
- Modify: `packages/benchmark/src/ai_benchmark/scheduler.py` (`run_experiment` :126-248 — collect per-task provenance, write `runs_dir/exp_id/manifest.json`, store it; `_run_once` :292 and the Docker branch :600-640 — real `environment_digest`, `image_id` in `metadata.json`)
- Modify: `packages/benchmark/src/ai_benchmark/reporting.py` §1 (render `manifest` summary table: task, commit[:12], env digest[:12], image id[:19] or `n/a`)
- Modify: `packages/cli/src/ai_cli/codebench.py:202-270` (`tasks build`: cache, skip, `--force`, table)
- Modify: `.gitignore` (`.codebench/`)
- Test: `packages/benchmark/tests/test_provenance.py`, `packages/benchmark/tests/test_storage.py`, `packages/benchmark/tests/test_scheduler.py`, `packages/cli/tests/test_tasks_build.py`

**Interfaces:**
- `environment_digest(task_dir: Path, dockerfile_rel: str) -> str` — sha256 of `b"dockerfile\0" + bytes` then for each file under `task_dir/source` (sorted relative POSIX path, skipping `__pycache__`/`.pyc`/`.pytest_cache`): `path.encode() + b"\0" + bytes`; hex digest.
- `@dataclass(frozen=True, slots=True) class ImageInfo: image_id: str; size_bytes: int`; `inspect_image(tag: str) -> ImageInfo | None` (`docker image inspect --format {{.Id}} {{.Size}} <tag>`, None on any failure).
- `class ImageCache` with `path: Path` (default `Path(".codebench/images.json")`), `load() -> dict[str, dict[str, Any]]`, `get(task_id) -> dict | None`, `put(task_id, *, tag, environment_digest, image_id, size_bytes) -> None` (adds `built_at` ISO UTC, writes sorted JSON atomically).
- `build_manifest(*, prompt_wrapper_version: str, docker: str | None, agents: dict[str, dict[str, Any]], tasks: dict[str, dict[str, Any]]) -> dict[str, Any]` — pure; shape per spec D8.
- Storage: `_MIGRATIONS: dict[int, list[str]] = {2: ["ALTER TABLE experiments ADD COLUMN provenance_json TEXT NOT NULL DEFAULT '{}'"]}`; `connect` applies versions `> current` and `<= SCHEMA_VERSION` inside one transaction each, skipping an `ALTER` whose column already exists, then inserts the version row; raises `ConfigurationError` when stored version `> SCHEMA_VERSION`.
- `tasks build` output: header `task_id  image  digest  size` then one row per task with `digest` = `image_id[7:19]` and `size` = MiB with one decimal, status suffix `built`/`cached`/`FAILED`; final `Build complete: {built} built, {cached} cached, {skipped} skipped.`

- [ ] **Step 1: Failing tests**: `test_environment_digest_stable_and_ignores_pycache`; `test_image_cache_roundtrip` (tmp path); `test_build_manifest_shape`; storage `test_migrate_v1_to_v2_preserves_rows` (create a v1 DB by executing the old `CREATE TABLE experiments` without the column and inserting a row + `schema_version (1)`, then `connect` → `provenance_json == "{}"`, row intact, latest version 2) and `test_newer_schema_rejected`; scheduler `test_scheduler_writes_manifest` (`runs/exp_test_1/manifest.json` exists, `tasks["example-task"]["environment_digest"]` is 64 hex, `experiments.provenance_json` equals the file); CLI `test_tasks_build_cached_skip` (patch `build_image`, `inspect_image` → `ImageInfo("sha256:abc", 1)`, use `--cache-path tmp`; second invocation prints `cached` and does not call `build_image`; `--force` calls it) and `test_tasks_build_outputs_table` (header present).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**. `tasks build` gets options `--force` and `--cache-path PATH` (default `.codebench/images.json`).
- [ ] **Step 4: Run** `uv run pytest packages/benchmark packages/cli packages/schemas -q` → PASS.
- [ ] **Step 5: Commit** `feat(benchmark): experiment provenance manifest, environment digests, image build cache (schema v2)`.

### Task 10: Solution overlays for the remaining 23 pilot tasks

**Files:**
- Create: `tasks/pilot/<id>/solution/files/<module>.py` for every pilot task except `example-task` (23 tasks)
- Test: `packages/benchmark/tests/test_pilot_oracles.py`

**Interfaces:**
- Consumes: `verify_task` (Task 8), `materialize_repo` (Task 5).

- [ ] **Step 1: Write the parametrized test**:

```python
PILOT = Path(__file__).resolve().parents[3] / "tasks" / "pilot"


@pytest.mark.parametrize(
    "task_dir",
    sorted(p for p in PILOT.iterdir() if (p / "task.toml").is_file()),
    ids=lambda p: p.name,
)
def test_pilot_task_is_working_oracle(task_dir, tmp_path):
    result = verify_task(task_dir, work_dir=tmp_path, use_docker=False)
    assert result.ok, result.errors
```

- [ ] **Step 2: Run** `uv run pytest packages/benchmark/tests/test_pilot_oracles.py -q` → 23 FAIL (missing overlay), 1 PASS.
- [ ] **Step 3: Author overlays** in three parallel batches (8/8/7 tasks). For each task: read `source/<module>.py`, `evaluator/tests/test_hidden.py`, `solution/README.md`; write the complete fixed module to `solution/files/<module>.py` (only files that change; usually one). Do not edit `source/`, `instruction.md`, `evaluator/` or `task.toml`. Prove each with `uv run codebench tasks verify <id>` → `OK`. If a hidden test cannot pass without changing the evaluator, STOP and report `ORACLE_BROKEN: <id> <reason>`.
- [ ] **Step 4: Run** the parametrized test → 24 passed.
- [ ] **Step 5: Commit** `feat(benchmark): verified reference solution overlays for all pilot tasks`.

### Task 11: `tasks init` scaffold

**Files:**
- Create: `packages/benchmark/src/ai_benchmark/task_scaffold.py`
- Modify: `packages/cli/src/ai_cli/codebench.py` (new `tasks init`)
- Test: `packages/benchmark/tests/test_task_scaffold.py`, `packages/cli/tests/test_tasks_init.py`

**Interfaces:**
- `RUN_TESTS_SH: str` — the exact text of `tasks/pilot/example-task/evaluator/run_tests.sh`; `DOCKERFILE: str` — the exact text of `tasks/pilot/example-task/environment/Dockerfile`.
- `scaffold_task(tasks_root: Path, *, task_id: str, suite: str = "pilot", title: str, category: str, description: str = "") -> Path` — refuses existing dir (`ConfigurationError`); writes `task.toml` (same keys/values as example-task, `commit` placeholder `"0"*40`, `[scoring]` all gates false), `instruction.md` (asks to fix `greet(name)` in `app.py` which currently returns `"Hello, "` without the name), `source/app.py` (buggy), `source/README.md`, `source/test_visible.py` (`greet("x").startswith("Hello")`), `environment/Dockerfile`, `evaluator/run_tests.sh` (chmod 755), `evaluator/tests/test_hidden.py` (`greet("Ada") == "Hello, Ada"`), `solution/README.md`, `solution/files/app.py` (fixed); then `materialize_repo(dir, check=False)` + `repin_task`. Returns the task dir.
- CLI `tasks init TASK_ID --title T --category C [--suite S] [--description D]` prints `Created <dir> (commit <sha>)`; exit `EXIT_TASK` if it exists.

- [ ] **Step 1: Failing tests**: `test_scaffold_creates_valid_verifiable_task` (`validate_task(dir, check_repo=True).ok`, `verify_task(dir, work_dir=tmp).ok`), `test_scaffold_refuses_existing`; CLI `test_tasks_init_then_validate` (`TASKS_ROOT` tmp).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run** `uv run pytest packages/benchmark packages/cli -q` → PASS.
- [ ] **Step 5: Commit** `feat(cli): tasks init scaffolds a verifiable task`.

### Task 12: Docs, todo, full gate

**Files:**
- Modify: `docs/codebench-tasks.md` (materialize/verify/init workflow, `solution/files/`, gate commands), `docs/codebench-results.md` (CI/sign-test/bootstrap paragraph, gate columns), `docs/codebench-configuration.md` (custom agents, if not done in Task 6), `README.md:147-158` (command list adds `tasks materialize|verify|init|build`), `tasks/todo-v0.2.md` (mark Task 2 done; add "Supplement: trust fixes" checklist referencing the design doc)
- Modify: `.clavity/local-anomalies.md` is local-only — do not commit; the anomaly is resolved by Task 2–4.

- [ ] **Step 1: Write the docs.**
- [ ] **Step 2: Run the full gate** (Global Constraints) → `ruff` clean, `format --check` clean, `ty` `All checks passed!`, pytest `N passed, 1 skipped` with N ≥ 142 + new tests. Then `uv build --all-packages` → succeeds and `dist/` contains `ai_integration_generic_cli-0.1.0-py3-none-any.whl`.
- [ ] **Step 3: Commit** `docs(codebench): document task verification, gates, statistics, custom agents`.
