"""Agent execution loop over a ``ChatModel`` and a ``PluginRegistry``."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from typing import Any, Protocol

from ai_agents.policy import AuthorizationPolicy, DefaultAuthorizationPolicy
from ai_core.errors import (
    AuthorizationError,
    ConfigurationError,
    OperationTimeoutError,
)
from ai_core.ids import new_id
from ai_plugins_sdk import Plugin, PluginRegistry, ToolSpec
from ai_runtime.models import ChatModel, GenerationRequest
from ai_schemas import Message, Usage


class TraceHook(Protocol):
    """Narrow observability hook. Services install logging/metrics/tracing here."""

    def on_step(self, event: dict[str, Any]) -> None: ...


class AgentConfig:
    """Execution budget. All bounds are explicit."""

    def __init__(
        self,
        *,
        max_steps: int = 5,
        timeout_seconds: float = 30.0,
        request_timeout_seconds: float = 30.0,
        tool_timeout_seconds: float = 10.0,
        run_id: str | None = None,
    ) -> None:
        if max_steps < 1:
            raise ConfigurationError("max_steps must be >= 1")
        if timeout_seconds <= 0 or request_timeout_seconds <= 0 or tool_timeout_seconds <= 0:
            raise ConfigurationError("timeouts must be positive")
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.tool_timeout_seconds = tool_timeout_seconds
        self.run_id = run_id or new_id("run")


class AgentResult:
    """Structured agent outcome."""

    def __init__(
        self,
        *,
        answer: str,
        steps: int,
        tool_calls: int,
        usage: Usage,
        completed: bool,
        run_id: str,
        trace: list[dict[str, Any]] | None = None,
    ) -> None:
        self.answer = answer
        self.steps = steps
        self.tool_calls = tool_calls
        self.usage = usage
        self.completed = completed
        self.run_id = run_id
        self.trace = trace or []


def to_model_tools(specs: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    """Map ``ToolSpec`` to OpenAI-style function tool definitions for the model."""
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": dict(spec.input_schema),
            },
        }
        for spec in specs
    ]


def _add_usage(total: Usage, step: Usage) -> Usage:
    return Usage(
        input_tokens=total.input_tokens + step.input_tokens,
        output_tokens=total.output_tokens + step.output_tokens,
        total_tokens=total.total_tokens + step.total_tokens,
    )


async def run_agent(
    model: ChatModel,
    plugins: Sequence[Plugin] | PluginRegistry,
    user_message: str,
    *,
    config: AgentConfig | None = None,
    policy: AuthorizationPolicy | None = None,
    system_prompt: str | None = None,
    hooks: Sequence[TraceHook] | None = None,
) -> AgentResult:
    """Run a bounded tool-using loop. The model never executes code directly."""
    cfg = config or AgentConfig()
    auth = policy or DefaultAuthorizationPolicy()
    registry = plugins if isinstance(plugins, PluginRegistry) else PluginRegistry(list(plugins))
    specs = registry.tool_specs()
    model_tools = to_model_tools(specs) or None

    messages: list[Message] = []
    if system_prompt:
        messages.append(Message(role="system", content=system_prompt))
    messages.append(Message(role="user", content=user_message))

    total_usage = Usage()
    trace: list[dict[str, Any]] = []
    tool_calls_made = 0

    async def _run() -> AgentResult:
        nonlocal total_usage, tool_calls_made
        for step in range(1, cfg.max_steps + 1):
            request = GenerationRequest(
                messages=list(messages),
                tools=model_tools,
                timeout_seconds=cfg.request_timeout_seconds,
                request_id=f"{cfg.run_id}:{step}",
            )
            try:
                result = await asyncio.wait_for(
                    model.generate(request), cfg.request_timeout_seconds
                )
            except TimeoutError as exc:
                raise OperationTimeoutError("model request timed out", operation="agent") from exc
            total_usage = _add_usage(total_usage, result.usage)
            event: dict[str, Any] = {
                "run_id": cfg.run_id,
                "step": step,
                "content": result.content,
                "tool_calls": [tc.name for tc in result.tool_calls],
            }
            trace.append(event)
            for hook in hooks or []:
                hook.on_step(dict(event))

            if not result.tool_calls:
                return AgentResult(
                    answer=result.content,
                    steps=step,
                    tool_calls=tool_calls_made,
                    usage=total_usage,
                    completed=True,
                    run_id=cfg.run_id,
                    trace=trace,
                )

            messages.append(
                Message(
                    role="assistant",
                    content=result.content or "(tool calls)",
                )
            )
            for call in result.tool_calls:
                tool_calls_made += 1
                entry = registry.get(call.name)
                if entry is None:
                    messages.append(
                        Message(
                            role="tool",
                            content=json.dumps({"error": f"unknown tool {call.name!r}"}),
                            name=call.name,
                            tool_call_id=call.id,
                        )
                    )
                    continue
                _, spec = entry
                if not auth.is_authorized(spec):
                    messages.append(
                        Message(
                            role="tool",
                            content=json.dumps({"error": f"tool {call.name!r} is not authorized"}),
                            name=call.name,
                            tool_call_id=call.id,
                        )
                    )
                    trace.append(
                        {
                            "run_id": cfg.run_id,
                            "step": step,
                            "authorization_denied": call.name,
                        }
                    )
                    continue
                try:
                    output = await asyncio.wait_for(
                        registry.invoke(call.name, dict(call.arguments)),
                        cfg.tool_timeout_seconds,
                    )
                    messages.append(
                        Message(
                            role="tool",
                            content=json.dumps(output),
                            name=call.name,
                            tool_call_id=call.id,
                        )
                    )
                except AuthorizationError as exc:
                    messages.append(
                        Message(
                            role="tool",
                            content=json.dumps({"error": str(exc)}),
                            name=call.name,
                            tool_call_id=call.id,
                        )
                    )
                except Exception as exc:
                    messages.append(
                        Message(
                            role="tool",
                            content=json.dumps({"error": f"{type(exc).__name__}: {exc}"}),
                            name=call.name,
                            tool_call_id=call.id,
                        )
                    )
        return AgentResult(
            answer=messages[-1].content if messages else "",
            steps=cfg.max_steps,
            tool_calls=tool_calls_made,
            usage=total_usage,
            completed=False,
            run_id=cfg.run_id,
            trace=trace,
        )

    return await asyncio.wait_for(_run(), cfg.timeout_seconds)
