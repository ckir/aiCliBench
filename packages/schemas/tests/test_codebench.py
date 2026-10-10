import pytest
from pydantic import ValidationError as PydanticValidationError

from ai_schemas import (
    AgentCapability,
    BenchmarkConfig,
    TaskDefinition,
    UsageRecord,
)
from ai_schemas.codebench import PROMPT_WRAPPER_PREAMBLE, PROMPT_WRAPPER_VERSION


def test_benchmark_config_defaults_and_invalid():
    cfg = BenchmarkConfig()
    assert cfg.execution.default_timeout_seconds == 900
    assert cfg.execution.parallelism == 1
    assert cfg.agents.claude.command == "claude"
    assert cfg.agents.antigravity.command == "agy"
    assert set(cfg.agents.enabled_agents()) == {"claude", "antigravity"}

    with pytest.raises(PydanticValidationError):
        BenchmarkConfig.model_validate({"execution": {"default_timeout_seconds": 0}})

    with pytest.raises(PydanticValidationError):
        BenchmarkConfig.model_validate(
            {
                "execution": {
                    "default_timeout_seconds": 900,
                    "global_max_timeout_seconds": 100,
                }
            }
        )


def test_task_definition_commit_and_paths():
    base = {
        "id": "example-task",
        "title": "Fix parser",
        "repository": "https://example.invalid/r.git",
        "commit": "0" * 40,
        "evaluator_command": ["bash", "/evaluator/run_tests.sh"],
    }
    task = TaskDefinition.model_validate(base)
    assert task.commit == "0" * 40

    with pytest.raises(PydanticValidationError):
        TaskDefinition.model_validate({**base, "commit": "main"})

    with pytest.raises(PydanticValidationError):
        TaskDefinition.model_validate({**base, "instruction_file": "../evil.md"})

    with pytest.raises(PydanticValidationError):
        TaskDefinition.model_validate({**base, "dockerfile": "/abs/Dockerfile"})


def test_usage_tolerates_missing():
    usage = UsageRecord()
    assert usage.input_tokens is None
    assert usage.cost_usd is None
    partial = UsageRecord.model_validate({"input_tokens": 10})
    assert partial.input_tokens == 10
    assert partial.output_tokens is None


def test_capability_defaults():
    cap = AgentCapability(agent_name="claude")
    assert cap.timeout_enforcement is True
    assert cap.reported_cost is False


def test_prompt_wrapper_versioned():
    assert PROMPT_WRAPPER_VERSION.startswith("codebench-")
    assert "hidden" in PROMPT_WRAPPER_PREAMBLE.lower()
