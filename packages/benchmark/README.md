# ai-benchmark

CodeBench Local domain: task registry, Git workspaces, Docker execution,
trusted evaluator, paired scheduler, SQLite storage, scoring, reporting,
export, redaction, and doctor checks.

- Depends on `ai-core`, `ai-schemas`, `ai-agents` only (inward flow).
- No provider SDKs, no MCP transport, no network at import.
- CLI (`ai-cli`) and provider adapters (`integrations/*`) compose this package.
