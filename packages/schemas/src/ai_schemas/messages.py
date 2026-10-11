"""Shared chat-message contracts (Pydantic v2, JSON-compatible)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]
"""The role of a chat message participant."""


class Message(BaseModel):
    """A single provider-independent chat message.

    Represents a single message in a chat conversation, independent of
    the underlying provider's API format.

    Attributes:
        role: The role of the message sender (system, user, assistant, or tool).
        content: The textual content of the message.
        name: Optional name of the participant (e.g., function name for tool calls).
        tool_call_id: Optional ID of the tool call this message responds to.
    """

    model_config = {"extra": "forbid"}

    role: Role
    content: str = Field(min_length=1)
    name: str | None = None
    tool_call_id: str | None = None
