"""OpenAI adapter configuration. Secrets come from the environment only."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 30.0


class OpenAIConfig(BaseModel):
    """Explicit adapter configuration. Never log ``api_key``."""

    model_config = {"extra": "forbid"}

    model: str = Field(default=DEFAULT_MODEL, min_length=1)
    api_key: str = Field(min_length=1, repr=False)
    base_url: str = Field(default=DEFAULT_BASE_URL, min_length=1)
    timeout_seconds: float = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)

    @classmethod
    def from_env(cls, overrides: dict[str, object] | None = None) -> OpenAIConfig:
        """Build config from environment with optional explicit overrides.

        Environment:
            OPENAI_API_KEY (required), OPENAI_MODEL, OPENAI_BASE_URL,
            OPENAI_TIMEOUT_SECONDS.
        """
        data: dict[str, object] = {
            "model": os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
            "base_url": os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL),
            "timeout_seconds": float(
                os.environ.get("OPENAI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
            ),
        }
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if overrides:
            data.update(overrides)
            if "api_key" not in overrides:
                data["api_key"] = api_key
        else:
            data["api_key"] = api_key
        return cls.model_validate(data)

    def redacted(self) -> str:
        return f"OpenAIConfig(model={self.model!r}, base_url={self.base_url!r}, api_key=***)"
