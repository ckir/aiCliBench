"""Token-usage contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Usage(BaseModel):
    """Normalized token usage. Providers map their native usage into this."""

    model_config = {"extra": "forbid"}

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

    def normalized(self) -> Usage:
        """Return a copy with a consistent total when the provider omits it."""
        total = self.total_tokens
        if total == 0:
            total = self.input_tokens + self.output_tokens
        return Usage(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=total,
        )
