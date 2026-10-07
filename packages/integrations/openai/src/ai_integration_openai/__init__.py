"""OpenAI provider adapter (httpx-based, no provider SDK leakage)."""

from ai_integration_openai.client import OpenAIChatModel
from ai_integration_openai.config import OpenAIConfig

__all__ = ["OpenAIChatModel", "OpenAIConfig"]
