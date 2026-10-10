"""Antigravity CLI configuration. Secrets come from the CLI login only."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AntigravityConfig(BaseModel):
    """Explicit adapter configuration. Never log secrets."""

    model_config = {"extra": "forbid"}

    command: str = Field(default="agy", min_length=1)
    model: str = Field(default="")
    timeout_seconds: float = Field(default=900, gt=0)
    output_format: str = Field(default="stream-json", min_length=1)
