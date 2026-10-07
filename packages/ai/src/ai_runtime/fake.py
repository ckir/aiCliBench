"""Deterministic fake model for unit tests, evals, and offline CI."""

from __future__ import annotations

from ai_core.ids import new_id
from ai_runtime.models import GenerationRequest, GenerationResult, ToolCall


class FakeChatModel:
    """Scripted chat model. Returns queued responses in order, then repeats the last."""

    def __init__(
        self,
        responses: list[GenerationResult] | None = None,
        *,
        provider: str = "fake",
        model_name: str = "fake-test",
    ) -> None:
        self._provider = provider
        self._model_name = model_name
        self._responses = list(responses) if responses else [GenerationResult(content="ok")]
        self.calls: list[GenerationRequest] = []

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls.append(request)
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        template = self._responses[index]
        # Give each tool call a stable id when the fixture omits one.
        tool_calls = [
            tc if tc.id else ToolCall(id=new_id("call"), name=tc.name, arguments=dict(tc.arguments))
            for tc in template.tool_calls
        ]
        return GenerationResult(
            content=template.content,
            tool_calls=tool_calls,
            usage=template.usage,
            model=self._model_name,
            finish_reason=template.finish_reason or "stop",
        )

    @staticmethod
    def text(content: str) -> GenerationResult:
        return GenerationResult(content=content, finish_reason="stop")

    @staticmethod
    def tool(name: str, args: dict[str, object], *, content: str = "") -> GenerationResult:
        return GenerationResult(
            content=content,
            tool_calls=[ToolCall(id=new_id("call"), name=name, arguments=dict(args))],
            finish_reason="tool_calls",
        )
