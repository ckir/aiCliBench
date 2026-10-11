"""Generic CLI adapter configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GenericCliConfig(BaseModel):
    """Explicit adapter configuration. Never log secrets."""

    model_config = {"extra": "forbid"}

    command: str = Field(min_length=1)
    args: list[str] = Field(default_factory=list)
    output_format: str = Field(default="text")
    model: str = Field(default="")
    model_flag: str = Field(default="")
    version_args: list[str] = Field(default_factory=lambda: ["--version"])
    timeout_seconds: float = Field(default=900, gt=0)