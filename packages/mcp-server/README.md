# ai-mcp-server

Reusable MCP server adapter over plugin capabilities.

- Discovery via `list_tools()` (maps `ToolSpec` to MCP definitions).
- `call_tool(name, args, authorized=...)` validates arguments, gates
  write/destructive tools on explicit authorization, bounds execution with a
  timeout, and normalizes failures.
- No business logic lives here; plugins own implementations.
