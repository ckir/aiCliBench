"""API service composition root. Thin wiring only; no domain logic."""

from __future__ import annotations

import logging
import os
from typing import TypedDict

from pydantic import BaseModel, Field

from ai_mcp_server import McpServer
from ai_plugin_example import ExamplePlugin
from ai_plugins_sdk import PluginRegistry

logger = logging.getLogger("ai_service_api")


class ServiceConfig(BaseModel):
    """Explicit service configuration validated at startup."""

    model_config = {"extra": "forbid"}

    service_name: str = Field(default="ai-service-api", min_length=1)
    log_level: str = Field(default="INFO", min_length=1)
    mcp_timeout_seconds: float = Field(default=10.0, gt=0)

    @classmethod
    def from_env(cls) -> ServiceConfig:
        return cls(
            service_name=os.environ.get("SERVICE_NAME", "ai-service-api"),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            mcp_timeout_seconds=float(os.environ.get("MCP_TIMEOUT_SECONDS", "10")),
        )


class ApiComposition(TypedDict):
    config: ServiceConfig
    registry: PluginRegistry
    server: McpServer


def configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))


def create_composition(config: ServiceConfig | None = None) -> ApiComposition:
    """Wire plugins, registry, and MCP adapter. Returns handles for the HTTP layer."""
    cfg = config or ServiceConfig.from_env()
    registry = PluginRegistry([ExamplePlugin()])  # type: ignore[list-item]
    server = McpServer(registry, timeout_seconds=cfg.mcp_timeout_seconds)
    return {"config": cfg, "registry": registry, "server": server}


def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ai-service-api"}
