# ai-agents

Agent runtime/orchestration: planning loop, tool selection via `PluginRegistry`,
conversation state, budgets/timeouts, authorization, tracing hooks.

- No provider SDK calls; depends on the `ai-runtime` `ChatModel` interface.
- The model never executes code; it only requests declared tools.
- `DefaultAuthorizationPolicy`: `read` allowed, `write`/`destructive` opt-in.
