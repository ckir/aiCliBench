"""CodeBench shared contracts (Pydantic v2, JSON-compatible).

Rules: no provider SDK dependencies, no database dependencies, no network access.
All records must tolerate missing usage/cost fields (unknown → None).
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)

PROMPT_WRAPPER_VERSION = "codebench-prompt-v1"
PROMPT_WRAPPER_PREAMBLE = (
    "You are working in a local repository checkout at the task working directory.\n"
    "Run only the visible tests/README commands for feedback; "
    "hidden acceptance tests will grade your change independently.\n"
    "Do not modify tests, evaluator scripts, or task metadata.\n"
)


class DataConfig(BaseModel):
    model_config = {"extra": "forbid"}

    directory: str = Field(default="runs", min_length=1)
    database: str = Field(default="runs/codebench.sqlite3", min_length=1)
    artifact_retention: Literal["all", "minimal"] = "all"


class ExecutionConfig(BaseModel):
    model_config = {"extra": "forbid"}

    default_timeout_seconds: int = Field(default=900, gt=0)
    global_max_timeout_seconds: int = Field(default=3600, gt=0)
    startup_grace_seconds: int = Field(default=10, ge=0)
    parallelism: int = Field(default=1, ge=1)
    network_enabled_for_agent: bool = False
    cpu_limit: float = Field(default=2, gt=0)
    memory_limit: str = Field(default="4g", min_length=1)
    pids_limit: int = Field(default=256, gt=0)
    container_user: str = Field(default="10001:10001", min_length=1)
    workspace_cleanup: Literal["retain", "remove"] = "retain"
    random_seed: int = Field(default=20261010)


class AgentInstanceConfig(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool = True
    command: str = Field(min_length=1)
    model: str = Field(default="")
    timeout_seconds: int = Field(default=900, gt=0)
    output_format: str = Field(default="", min_length=0)


class CustomAgentConfig(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool = True
    command: str = Field(min_length=1)
    args: list[str] = Field(default_factory=list)
    output_format: Literal["json", "jsonl", "text"] = "text"
    model: str = Field(default="")
    model_flag: str = Field(default="")
    version_args: list[str] = Field(default_factory=lambda: ["--version"])
    timeout_seconds: int = Field(default=900, gt=0)


class AgentsConfig(BaseModel):
    model_config = {"extra": "forbid"}

    claude: AgentInstanceConfig = Field(
        default_factory=lambda: AgentInstanceConfig(command="claude", output_format="json")
    )
    antigravity: AgentInstanceConfig = Field(
        default_factory=lambda: AgentInstanceConfig(command="agy", output_format="stream-json")
    )
    custom: dict[str, CustomAgentConfig] = Field(default_factory=dict)

    def enabled_agents(self) -> list[str]:
        out: list[str] = []
        if self.claude.enabled:
            out.append("claude")
        if self.antigravity.enabled:
            out.append("antigravity")
        for name, cfg in self.custom.items():
            if cfg.enabled:
                out.append(name)
        return out

    @model_validator(mode="after")
    def _validate_custom_names(self) -> AgentsConfig:
        reserved = {"claude", "antigravity"}
        for name in self.custom:
            if name in reserved:
                raise ValueError(f"invalid custom agent name: {name!r} (reserved)")
            if not name.islower() or not name[0].isalpha():
                raise ValueError(
                    f"invalid custom agent name: {name!r} (must start with letter, lowercase)"
                )
            if not all(c.isalnum() or c in "-_" for c in name):
                raise ValueError(f"invalid custom agent name: {name!r} (only alphanumeric, -, _)")
            if len(name) > 32:
                raise ValueError(f"invalid custom agent name: {name!r} (max 32 chars)")
        return self


class ReportConfig(BaseModel):
    model_config = {"extra": "forbid"}

    title: str = Field(default="CodeBench Local", min_length=1)
    include_full_logs: bool = False


class BenchmarkConfig(BaseModel):
    """Resolved benchmark configuration (§6)."""

    model_config = {"extra": "forbid"}

    data: DataConfig = Field(default_factory=DataConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)

    @model_validator(mode="after")
    def _check_timeouts(self) -> BenchmarkConfig:
        if self.execution.default_timeout_seconds > self.execution.global_max_timeout_seconds:
            raise ValueError(
                "execution.default_timeout_seconds must not exceed "
                "execution.global_max_timeout_seconds"
            )
        for name, inst in (
            ("claude", self.agents.claude),
            ("antigravity", self.agents.antigravity),
        ):
            if inst.timeout_seconds > self.execution.global_max_timeout_seconds:
                raise ValueError(
                    f"agents.{name}.timeout_seconds exceeds execution.global_max_timeout_seconds"
                )
        for name, inst in self.agents.custom.items():
            if inst.timeout_seconds > self.execution.global_max_timeout_seconds:
                raise ValueError(
                    f"agents.custom.{name}.timeout_seconds exceeds "
                    "execution.global_max_timeout_seconds"
                )
        return self


class TaskEnvironment(BaseModel):
    model_config = {"extra": "forbid"}

    working_directory: str = Field(default="/workspace", min_length=1)
    setup_command: list[str] = Field(default_factory=list)


class TaskScoring(BaseModel):
    model_config = {"extra": "forbid"}

    acceptance_weight: float = Field(default=1.0, ge=0)
    build_required: bool = False
    lint_required: bool = False
    typecheck_required: bool = False
    build_command: list[str] = Field(default_factory=list)
    lint_command: list[str] = Field(default_factory=list)
    typecheck_command: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_gate_commands(self) -> TaskScoring:
        if self.build_required and not self.build_command:
            raise ValueError("build_required needs build_command")
        if self.lint_required and not self.lint_command:
            raise ValueError("lint_required needs lint_command")
        if self.typecheck_required and not self.typecheck_command:
            raise ValueError("typecheck_required needs typecheck_command")
        return self


class TaskDefinition(BaseModel):
    """Validated task.toml content (§7.1). Paths are task-relative."""

    model_config = {"extra": "forbid"}

    schema_version: int = Field(default=1, ge=1)
    id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1)
    category: str = Field(default="general", min_length=1)
    suite: str = Field(default="pilot", min_length=1)
    description: str = Field(default="")
    repository: str = Field(min_length=1)
    commit: str = Field(min_length=40, max_length=40)
    instruction_file: str = Field(default="instruction.md", min_length=1)
    dockerfile: str = Field(default="environment/Dockerfile", min_length=1)
    evaluator_command: list[str] = Field(min_length=1)
    timeout_seconds: int = Field(default=900, gt=0)
    max_test_seconds: int = Field(default=300, gt=0)
    cpu_limit: float | None = Field(default=None, gt=0)
    memory_limit: str | None = None
    pids_limit: int | None = Field(default=None, gt=0)
    network_enabled_for_agent: bool = False
    tags: list[str] = Field(default_factory=list)
    environment: TaskEnvironment = Field(default_factory=TaskEnvironment)
    scoring: TaskScoring = Field(default_factory=TaskScoring)

    @field_validator("id")
    @classmethod
    def _check_id(cls, value: str) -> str:
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$", value):
            raise ValueError(f"invalid task id: {value!r}")
        return value

    @field_validator("commit")
    @classmethod
    def _check_commit(cls, value: str) -> str:
        if not _FULL_SHA_RE.match(value):
            raise ValueError("commit must be a full 40-char Git SHA")
        return value.lower()

    @field_validator("instruction_file", "dockerfile")
    @classmethod
    def _check_relative(cls, value: str) -> str:
        if not value or value.startswith("/") or ".." in value.split("/"):
            raise ValueError(f"task-relative path must not escape: {value!r}")
        return value


class AgentCapability(BaseModel):
    """What an adapter can truthfully do (§8.4). Unavailable shown, not faked."""

    model_config = {"extra": "forbid"}

    agent_name: str = Field(min_length=1)
    non_interactive: bool = False
    model_selection: bool = False
    structured_output: bool = False
    reported_model: bool = False
    usage_telemetry: bool = False
    reported_cost: bool = False
    timeout_enforcement: bool = True
    cancellation: bool = True


class UsageRecord(BaseModel):
    """Tolerant usage record (§12.3). All fields optional; unknown → None."""

    model_config = {"extra": "forbid"}

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cache_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    raw: dict[str, Any] = Field(default_factory=dict)


class ExperimentRecord(BaseModel):
    model_config = {"extra": "forbid"}

    id: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    started_at: str | None = None
    ended_at: str | None = None
    status: str = Field(default="running", min_length=1)
    suite: str = Field(min_length=1)
    task_ids: list[str] = Field(min_length=1)
    agent_names: list[str] = Field(min_length=1)
    repeat_count: int = Field(ge=1)
    random_seed: int
    resolved_config: dict[str, Any] = Field(default_factory=dict)
    host_info: dict[str, Any] = Field(default_factory=dict)
    tool_versions: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    model_config = {"extra": "forbid"}

    id: str = Field(min_length=1)
    experiment_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    repetition: int = Field(ge=1)
    pair_key: str = Field(min_length=1)
    order_index: int = Field(ge=0)
    status: str = Field(min_length=1)
    requested_model: str | None = None
    reported_model: str | None = None
    cli_version: str | None = None
    starting_commit: str = Field(default="")
    instruction_sha256: str = Field(default="")
    environment_digest: str = Field(default="")
    evaluator_digest: str = Field(default="")
    started_at: str = Field(default="")
    ended_at: str = Field(default="")
    elapsed_seconds: float = Field(default=0.0, ge=0)
    exit_code: int | None = None
    error_category: str | None = None
    error_message: str | None = None
    usage: UsageRecord = Field(default_factory=UsageRecord)
    artifact_dir: str = Field(default="")


class EvaluationRecord(BaseModel):
    model_config = {"extra": "forbid"}

    id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    acceptance_pass: bool | None = None
    exit_code: int | None = None
    duration_seconds: float = Field(default=0.0, ge=0)
    tests_passed: int | None = Field(default=None, ge=0)
    tests_failed: int | None = Field(default=None, ge=0)
    tests_skipped: int | None = Field(default=None, ge=0)
    build_pass: bool | None = None
    lint_pass: bool | None = None
    typecheck_pass: bool | None = None
    regression_pass: bool | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    evaluator_version: str = Field(default="")


class ArtifactRecord(BaseModel):
    model_config = {"extra": "forbid"}

    id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    sha256: str = Field(default="")
    size_bytes: int = Field(default=0, ge=0)
    redacted: bool = False
    created_at: str = Field(default="")
