"""Shared chat-message contracts (Pydantic v2, JSON-compatible)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class Message(BaseModel):
    """A single provider-independent chat message."""

    model_config = {"extra": "forbid"}

    role: Role
    content: str = Field(min_length=1)
    name: str | None = None
    tool_call_id: str | None = None
