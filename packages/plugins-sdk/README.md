# ai-plugins-sdk

Plugin authoring API: metadata, tool specifications, invocation interface, registry.

## Rules

- Transport-independent: plugins must be usable without MCP.
- Side effects are classified as `read` / `write` / `destructive`.
- Write/destructive tools require explicit authorization by the caller.
- No provider SDK imports.
