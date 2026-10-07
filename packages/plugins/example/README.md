# ai-plugin-example

Deterministic example plugin demonstrating plugin boundaries.

- Tool: `echo` (`READ` effect, no authorization required).
- Input: `{ "text": string(1..10000) }`. Output: `{ "text", "length" }`.
- No network, no credentials, no MCP dependency.

## Security notes

No scopes or permissions required. Safe to expose without authorization gating
(effect is `read`). If you add write/destructive tools, declare
`ToolEffect.WRITE` / `DESTRUCTIVE` so runtimes gate them.
