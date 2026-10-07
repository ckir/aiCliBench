import asyncio
from typing import Any

import pytest

from ai_evals import EvalCase, run_eval_case, run_eval_suite, summarize
from ai_plugins_sdk import PluginMetadata, ToolSpec
from ai_runtime import FakeChatModel


class _EchoPlugin:
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(name="echo", version="0.1.0", description="echo")

    def tools(self) -> list[ToolSpec]:
        return [ToolSpec(name="echo", description="Echo", input_schema={"type": "object"})]

    async def invoke(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"text": "hi"}


def test_evals_package_imports():
    import ai_evals

    assert ai_evals is not None


@pytest.mark.eval
def test_deterministic_slice_echo():
    """Vertical-slice eval: fake model -> echo tool -> grounded answer."""

    async def _run() -> None:
        case = EvalCase(
            id="echo-001",
            description="Model must call echo then answer with the echoed text.",
            user_message="echo hello",
            expected_contains="hello",
            expected_tool="echo",
        )
        model = FakeChatModel(
            responses=[
                FakeChatModel.tool("echo", {"text": "hello"}),
                FakeChatModel.text("you said hello"),
            ]
        )
        result = await run_eval_case(case, model, [_EchoPlugin()])  # type: ignore[list-item]
        assert result.passed, result.details
        assert result.provider == "fake"
        assert result.config["max_steps"] == 5

    asyncio.run(_run())


@pytest.mark.eval
def test_eval_failure_recorded():
    async def _run() -> None:
        case = EvalCase(
            id="echo-002",
            description="Expectation intentionally unmet.",
            user_message="hi",
            expected_contains="no-such-phrase",
        )
        model = FakeChatModel(responses=[FakeChatModel.text("hello")])
        result = await run_eval_case(case, model, [_EchoPlugin()])  # type: ignore[list-item]
        assert not result.passed
        assert "no-such-phrase" in result.details

    asyncio.run(_run())


@pytest.mark.eval
def test_eval_suite_summary():
    async def _run() -> None:
        cases = [
            EvalCase(id="a", description="a", user_message="hi", expected_contains="hello"),
            EvalCase(id="b", description="b", user_message="hi", expected_contains="missing"),
        ]
        model = FakeChatModel(responses=[FakeChatModel.text("hello")])
        results = await run_eval_suite(cases, model, [_EchoPlugin()])  # type: ignore[list-item]
        summary = summarize(results)
        assert summary == {"total": 2, "passed": 1, "failed": 1}

    asyncio.run(_run())
