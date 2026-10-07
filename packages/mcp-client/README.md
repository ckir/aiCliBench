# ai-mcp-client

Client abstraction for MCP servers.

- `McpClient`: `list_tools` / `call_tool` protocol.
- `InProcessMcpClient`: delegates to an in-process server (tests, single-process services).
- Remote transports (stdio/SSE/HTTP) implement the same protocol; business logic
  never depends on transport details.
