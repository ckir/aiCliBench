"""Example capability: deterministic echo. No network, no credentials.

This module owns the business logic. MCP, HTTP, CLI, and agent runtimes are
all adapters around :func:`echo_text`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EchoInput(BaseModel):
    model_config = {"extra": "forbid"}

    text: str = Field(min_length=1, max_length=10000)


class EchoOutput(BaseModel):
    model_config = {"extra": "forbid"}

    text: str
    length: int


def echo_text(text: str) -> EchoOutput:
    """Echo ``text`` with its character length. Pure and deterministic."""
    validated = EchoInput(text=text)
    return EchoOutput(text=validated.text, length=len(validated.text))
