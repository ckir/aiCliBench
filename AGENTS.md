# AGENT SYSTEM INSTRUCTIONS — AI/MCP/PLUGIN MONOREPO

You are the coding agent responsible for implementing this repository.

Read:
1. `README.md`
2. `ARCHITECTURE.md`
3. `AGENT_HANDOFF.md`

before making architectural changes.

## 1. Primary objective

Build a production-quality Python monorepo for AI capabilities, MCP servers/clients, plugins, integrations, agents, and deployable services.

Optimize for:
- explicit boundaries;
- independent package ownership;
- typed interfaces;
- deterministic local/CI checks;
- reproducible builds;
- easy plugin creation;
- provider independence;
- safe automation;
- independently releasable packages.

Do not optimize for minimizing the number of files.

## 2. Non-negotiable architecture

### Core dependency rule

Dependencies flow inward:

```text
services
  -> agents
  -> ai / mcp / plugins-sdk
  -> schemas / core
```

Implementations may depend on abstractions, but abstractions must not import implementations.

Forbidden examples:
- `core` importing OpenAI SDK;
- `plugins-sdk` importing a concrete Slack plugin;
- an MCP transport implementation defining business/domain logic;
- provider SDK types appearing in public core interfaces.

### Plugin rule

A plugin must be independently testable and independently buildable.

A plugin should expose a small contract such as:

```python
class Plugin(Protocol):
    @property
    def name(self) -> str: ...

    def tools(self) -> Sequence[ToolSpec]: ...
```

Use a real abstract base class only when shared behavior/state is required. Prefer Protocols for extension points.

### MCP rule

MCP transport concerns belong in MCP packages.

Business logic should implement tool capabilities independently of whether they are exposed through:
- MCP;
- HTTP;
- CLI;
- an agent runtime;
- tests.

Do not put business logic inside MCP request handlers.

### AI provider rule

Provider-specific SDKs are adapters.

Do not expose provider SDK request/response classes from `packages/ai` public APIs.

Normalize only the concepts the product actually needs. Do not create an enormous universal LLM abstraction for hypothetical future providers.

## 3. Python style

- Type all public functions/methods.
- Prefer immutable data models where practical.
- Use Pydantic v2 for externally validated structured data.
- Prefer `dataclass(frozen=True, slots=True)` for small internal value objects when Pydantic is unnecessary.
- Use explicit exceptions.
- Never catch `Exception` broadly without a clear boundary/reason.
- Preserve exception context with `raise ... from exc`.
- Avoid global mutable state.
- Avoid hidden network calls during import.
- Avoid import-time initialization of clients.
- Prefer dependency injection at application boundaries.

## 4. Async

Use async for network-bound operations.

Rules:
- do not call blocking network clients from async code;
- use `httpx.AsyncClient` for HTTP;
- make ownership/lifecycle of clients explicit;
- close clients deterministically;
- do not create a new HTTP client for every request if a long-lived client is appropriate.

## 5. Configuration and secrets

- Configuration is explicit.
- Secrets come from environment variables or the deployment secret manager.
- Never commit credentials.
- Never log secrets, API keys, authorization headers, or full provider responses if they may contain sensitive data.
- `.env.example` may contain variable names and safe placeholders only.
- Local `.env` files must be gitignored.

## 6. AI safety/robustness

Treat model output as untrusted input.

Validate structured model output before using it.

Tool calls must be:
- explicitly declared;
- schema validated;
- authorized;
- observable;
- bounded where appropriate.

Never allow a model to dynamically execute arbitrary Python/shell code.

For destructive/external side-effecting tools, define an explicit authorization/confirmation boundary.

## 7. MCP

For MCP tools:
- define stable names;
- provide concise descriptions;
- use explicit JSON/Pydantic schemas;
- validate all arguments;
- return structured results where possible;
- avoid leaking credentials;
- test malformed inputs;
- test tool discovery;
- test successful invocation;
- test error behavior.

If the MCP SDK has changed, use the currently supported API instead of copying an outdated example.

## 8. Testing

Every package gets tests.

At minimum:
- unit tests for deterministic domain logic;
- contract tests for public interfaces;
- MCP protocol/transport tests where applicable;
- integration tests for real adapters;
- evals for model behavior.

Network/provider tests must be explicitly marked and should not run accidentally on every local commit.

Tests must not depend on production credentials.

## 9. Evals

Treat deterministic tests and model evals differently.

A model eval must record:
- case/input;
- expected behavior or rubric;
- model/provider;
- relevant configuration;
- result;
- pass/fail;
- enough metadata to reproduce it.

Avoid making CI depend on a live commercial model unless the workflow explicitly opts into that behavior.

Prefer mocked/fake providers for PR CI and scheduled live-provider evals for regression detection.

## 10. Git workflow

Use Conventional Commits.

Examples:

```text
feat(plugins-github): add issue search tool
fix(mcp-server): reject invalid tool arguments
feat(ai)!: remove legacy completion interface
chore: update uv lockfile
```

Do not manually maintain changelogs if release-please owns them.

## 11. GitHub Actions

All normal CI jobs use least-privilege permissions.

Do not grant:
```yaml
permissions:
  contents: write
```
to normal test jobs.

Third-party actions should be pinned to immutable commit SHAs in production. Keep a version comment beside the SHA.

Use dependency caching.

Use concurrency controls to cancel superseded PR runs where appropriate.

Never expose write-capable secrets to untrusted pull requests.

## 12. Release behavior

Packages are independently versioned unless the product explicitly requires lockstep releases.

release-please manifest mode owns:
- versions;
- release PRs;
- changelog updates;
- GitHub releases.

Publishing happens only from trusted release workflows.

PyPI publishing uses Trusted Publishing/OIDC, not long-lived API tokens.

## 13. Completion standard

Before declaring implementation complete:

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
uv build
```

Inspect:
- package dependency graph;
- workflow permissions;
- action pinning;
- release flow;
- publishing flow;
- secret handling;
- Dockerfiles if present;
- plugin registration;
- MCP tool schemas;
- tests.

If a step requires human GitHub/PyPI configuration, document it explicitly instead of pretending it is complete.
