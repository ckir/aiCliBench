"""OpenAI ``ChatModel`` adapter over ``httpx.AsyncClient``.

Provider SDK types never escape this package. All failures are normalized to
``ProviderError`` / ``OperationTimeoutError`` / ``ConfigurationError``.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from ai_core.errors import (
    ConfigurationError,
    OperationTimeoutError,
    ProviderError,
)
from ai_core.ids import new_id
from ai_integration_openai.config import OpenAIConfig
from ai_runtime.models import GenerationRequest, GenerationResult, ToolCall
from ai_schemas import Usage

_PROVIDER = "openai"


class OpenAIChatModel:
    """Long-lived adapter. Owns its HTTP client unless one is injected."""

    def __init__(
        self,
        config: OpenAIConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not config.api_key:
            raise ConfigurationError("OPENAI_API_KEY is missing")
        self._config = config
        self._owned = client is None
        self._client = client or httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout_seconds),
        )

    @property
    def provider(self) -> str:
        return _PROVIDER

    @property
    def model_name(self) -> str:
        return self._config.model

    async def aclose(self) -> None:
        """Close the owned HTTP client. No-op when the client was injected."""
        if self._owned:
            await self._client.aclose()

    async def __aenter__(self) -> OpenAIChatModel:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    def _payload(self, request: GenerationRequest) -> dict[str, Any]:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = request.tools
        return payload

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        timeout = request.timeout_seconds or self._config.timeout_seconds
        headers = {"Authorization": f"Bearer {self._config.api_key}"}
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        try:
            response = await self._client.post(
                url,
                json=self._payload(request),
                headers=headers,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise OperationTimeoutError(
                f"openai request timed out after {timeout}s", operation="generate"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc), provider=_PROVIDER, retryable=True) from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise ProviderError(
                f"openai request failed with status {response.status_code}",
                provider=_PROVIDER,
                retryable=True,
            )
        if response.status_code >= 400:
            raise ProviderError(
                f"openai request failed with status {response.status_code}",
                provider=_PROVIDER,
                retryable=False,
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise ProviderError("invalid JSON from openai", provider=_PROVIDER) from exc
        return self._to_result(body)

    def _to_result(self, body: dict[str, Any]) -> GenerationResult:
        try:
            choices = body["choices"]
            message = choices[0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("malformed openai response envelope", provider=_PROVIDER) from exc

        content = message.get("content") or ""
        tool_calls: list[ToolCall] = []
        for raw in message.get("tool_calls") or []:
            try:
                fn = raw["function"]
                name = fn["name"]
                raw_args = fn.get("arguments", "{}") or "{}"
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                call_id = raw.get("id") or new_id("call")
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderError("malformed openai tool_call", provider=_PROVIDER) from exc
            tool_calls.append(ToolCall(id=call_id, name=name, arguments=args))

        usage = Usage()
        raw_usage = body.get("usage") or {}
        if isinstance(raw_usage, dict):
            usage = Usage(
                input_tokens=int(raw_usage.get("prompt_tokens", 0) or 0),
                output_tokens=int(raw_usage.get("completion_tokens", 0) or 0),
                total_tokens=int(raw_usage.get("total_tokens", 0) or 0),
            ).normalized()

        return GenerationResult(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            model=str(body.get("model", self._config.model)),
            finish_reason=str(choices[0].get("finish_reason", "") or ""),
        )
