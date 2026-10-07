# Recommended Implementation Order

1. `core`
2. `schemas`
3. `plugins-sdk`
4. `ai`
5. provider adapters
6. `mcp-core`
7. `mcp-testing`
8. `mcp-server`
9. `mcp-client`
10. concrete plugins
11. `agents`
12. `evals`
13. services
14. CI/security
15. release/publish

Do not implement all integrations before validating the contracts. Build one vertical slice first:

```text
one provider
  -> one model abstraction
  -> one plugin
  -> one tool
  -> one MCP server
  -> one agent
  -> one deterministic eval
  -> one CI path
  -> one release
```

Once that slice is sound, generalize.
