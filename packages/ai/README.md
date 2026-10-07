# ai-runtime

Product-level model abstraction: `ChatModel`, `GenerationRequest`, `GenerationResult`,
`ToolCall`, structured-output validation, and a deterministic `FakeChatModel`.

## Rules

- Provider SDK types never escape adapters.
- Production code must be testable without network access via `FakeChatModel`.
- Structured model output is validated before use.
