"""Worker composition root: runs bounded agent jobs. No domain logic here."""

from __future__ import annotations

import logging
import os

from pydantic import BaseModel, Field

from ai_agents import AgentConfig, run_agent
from ai_plugin_example import ExamplePlugin
from ai_runtime.models import ChatModel

logger = logging.getLogger("ai_service_worker")


class WorkerConfig(BaseModel):
    model_config = {"extra": "forbid"}

    worker_name: str = Field(default="ai-service-worker", min_length=1)
    max_steps: int = Field(default=5, ge=1)

    @classmethod
    def from_env(cls) -> WorkerConfig:
        return cls(
            worker_name=os.environ.get("WORKER_NAME", "ai-service-worker"),
            max_steps=int(os.environ.get("WORKER_MAX_STEPS", "5")),
        )


async def run_job(
    model: ChatModel, user_message: str, *, config: WorkerConfig | None = None
) -> str:
    """Execute one bounded agent job with the example plugin. Returns the answer."""
    cfg = config or WorkerConfig.from_env()
    result = await run_agent(
        model,
        [ExamplePlugin()],  # type: ignore[list-item]
        user_message,
        config=AgentConfig(max_steps=cfg.max_steps),
    )
    logger.info("worker job completed run_id=%s completed=%s", result.run_id, result.completed)
    return result.answer


def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ai-service-worker"}
