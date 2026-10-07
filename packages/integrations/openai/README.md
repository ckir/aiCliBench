# ai-integration-openai

OpenAI `ChatModel` adapter over `httpx.AsyncClient`.

- Config from environment (`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`,
  `OPENAI_TIMEOUT_SECONDS`); secrets are never logged.
- Long-lived `httpx.AsyncClient` with explicit ownership (`aclose()` / context manager).
- Failures normalized to `ProviderError` / `OperationTimeoutError`.
- Tests use `httpx.MockTransport`; live test is marked `live` and skipped without credentials.
