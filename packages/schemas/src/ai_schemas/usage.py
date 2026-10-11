"""Token-usage contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Usage(BaseModel):
    """Normalized token usage. Providers map their native usage into this.

    Attributes:
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.
        total_tokens: Total tokens (input + output). May be provided by the
            provider or computed as the sum of input and output tokens.
    """

    model_config = {"extra": "forbid"}

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

    def normalized(self) -> Usage:
        """Return a copy with a consistent total when the provider omits it.

        If ``total_tokens`` is zero, it is computed as the sum of
        ``input_tokens`` and ``output_tokens``. Otherwise, the provided
        ``total_tokens`` is preserved.

        Returns:
            A new ``Usage`` instance with a consistent ``total_tokens`` value.
        """
        total = self.total_tokens
        if total == 0:
            total = self.input_tokens + self.output_tokens
        return Usage(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=total,
        )
