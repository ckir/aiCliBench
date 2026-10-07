import pytest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ai_core.errors import ValidationError
from ai_runtime import (
    FakeChatModel,
    GenerationRequest,
    GenerationResult,
    parse_structured_output,
)
from ai_schemas import Message


def test_ai_package_imports():
    import ai_runtime

    assert ai_runtime is not None


def test_generation_request_validation():
    with pytest.raises(PydanticValidationError, match="messages"):
        GenerationRequest(messages=[])


async def _fake_roundtrip() -> GenerationResult:
    model = FakeChatModel(responses=[FakeChatModel.text("hello")])
    result = await model.generate(GenerationRequest(messages=[Message(role="user", content="hi")]))
    assert result.content == "hello"
    assert model.provider == "fake"
    return result


def test_fake_model_text():
    import asyncio

    result = asyncio.run(_fake_roundtrip())
    assert result.finish_reason == "stop"


def test_fake_model_tool_call():
    import asyncio

    async def _run() -> None:
        model = FakeChatModel(responses=[FakeChatModel.tool("echo", {"text": "hi"})])
        result = await model.generate(
            GenerationRequest(messages=[Message(role="user", content="hi")])
        )
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "echo"

    asyncio.run(_run())


def test_structured_output_validation():
    class _Answer(BaseModel):
        model_config = {"extra": "forbid"}
        value: int

    ok = parse_structured_output(_Answer, {"value": 3})
    assert ok.value == 3

    ok2 = parse_structured_output(_Answer, '{"value": 4}')
    assert ok2.value == 4

    with pytest.raises(ValidationError):
        parse_structured_output(_Answer, {"value": "not-an-int"})

    with pytest.raises(ValidationError):
        parse_structured_output(_Answer, 42)
