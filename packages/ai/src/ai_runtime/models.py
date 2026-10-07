"""Product-level model abstraction. Intentionally small."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from ai_schemas import Message, Usage


class ToolCall(BaseModel):
    """A model-requested tool invocation. Arguments are JSON-compatible."""

    model_config = {"extra": "forbid"}

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class GenerationRequest(BaseModel):
    """Provider-independent generation input."""

    model_config = {"extra": "forbid"}

    messages: list[Message] = Field(min_length=1)
    tools: list[dict[str, Any]] | None = None
    max_tokens: int | None = Field(default=None, gt=0)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    request_id: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)


class GenerationResult(BaseModel):
    """Normalized generation output. Provider SDK types must never appear here."""

    model_config = {"extra": "forbid"}

    content: str = Field(default="")
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    model: str = Field(default="")
    finish_reason: str = Field(default="")


class ChatModel(Protocol):
    """Minimal chat-model interface implemented by provider adapters and fakes."""

    @property
    def provider(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def generate(self, request: GenerationRequest) -> GenerationResult: ...
