import asyncio
import json
import os

import httpx
import pytest
from pydantic import ValidationError as PydanticValidationError

from ai_core.errors import ConfigurationError, OperationTimeoutError, ProviderError
from ai_integration_openai import OpenAIChatModel, OpenAIConfig
from ai_runtime import GenerationRequest
from ai_schemas import Message


def _request() -> GenerationRequest:
    return GenerationRequest(messages=[Message(role="user", content="hi")])


def test_openai_adapter_imports():
    import ai_integration_openai

    assert ai_integration_openai is not None


def test_config_from_env_requires_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(PydanticValidationError, match="api_key"):
        OpenAIConfig.from_env()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    config = OpenAIConfig.from_env()
    assert config.api_key == "test-key"
    assert "test-key" not in config.redacted()


def test_generate_text_and_usage():
    payload = {
        "model": "gpt-4o-mini",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "hello"},
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
    }
    config = OpenAIConfig(api_key="k", model="gpt-4o-mini")

    async def _run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
        ) as http:
            model = OpenAIChatModel(config, client=http)
            result = await model.generate(_request())
            assert result.content == "hello"
            assert result.usage.total_tokens == 7
            assert model.provider == "openai"

    asyncio.run(_run())


def test_generate_tool_call_parses_json_arguments():
    payload = {
        "model": "gpt-4o-mini",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "echo",
                                "arguments": json.dumps({"text": "hi"}),
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {},
    }
    config = OpenAIConfig(api_key="k")

    async def _run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
        ) as http:
            model = OpenAIChatModel(config, client=http)
            result = await model.generate(_request())
            assert len(result.tool_calls) == 1
            assert result.tool_calls[0].arguments == {"text": "hi"}

    asyncio.run(_run())


def test_generate_normalizes_http_errors():
    config = OpenAIConfig(api_key="k")

    async def _run(status: int, retryable: bool) -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(status, json={}))
        ) as http:
            model = OpenAIChatModel(config, client=http)
            with pytest.raises(ProviderError) as excinfo:
                await model.generate(_request())
            assert excinfo.value.retryable is retryable

    asyncio.run(_run(429, True))
    asyncio.run(_run(500, True))
    asyncio.run(_run(400, False))


def test_generate_timeout_normalized():
    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow")

    async def _run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as http:
            model = OpenAIChatModel(OpenAIConfig(api_key="k"), client=http)
            with pytest.raises(OperationTimeoutError):
                await model.generate(_request())

    asyncio.run(_run())


def test_missing_key_rejected():
    with pytest.raises(ConfigurationError):
        OpenAIChatModel(OpenAIConfig.model_construct(api_key=""))


@pytest.mark.live
def test_live_openai_smoke():
    """Opt-in live check. Requires OPENAI_API_KEY; never runs in PR CI."""
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    config = OpenAIConfig.from_env()

    async def _run() -> None:
        async with OpenAIChatModel(config) as model:
            result = await model.generate(_request())
            assert result.content is not None

    asyncio.run(_run())
