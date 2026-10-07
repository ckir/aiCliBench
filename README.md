# AI / MCP / Plugin Monorepo — v2 Blueprint

This repository is an implementation blueprint for an automation-first Python monorepo focused on AI applications, agents, MCP, plugins, integrations, SDKs, and deployable services.

## Core philosophy

1. Protocols and domain contracts live in small, stable packages.
2. Providers and integrations are adapters behind explicit interfaces.
3. Plugins are independently versioned packages.
4. MCP servers expose plugin/tool capabilities without coupling the business logic to MCP transport.
5. AI provider code never leaks into core business logic.
6. Evals are first-class and run separately from deterministic unit tests.
7. Every package is independently buildable and releasable.
8. `uv` is the only Python environment/dependency/build workflow.
9. GitHub Actions is the automation plane.
10. Manual release/version/changelog work should be exceptional.

## Recommended package graph

```text
packages/
├── core/                 # stable domain primitives and shared errors
├── schemas/              # shared Pydantic models / JSON schemas
├── ai/                   # model/provider abstraction
├── agents/               # agent runtime and orchestration
├── mcp-core/             # MCP-neutral contracts and utilities
├── mcp-client/           # MCP client abstraction
├── mcp-server/           # reusable MCP server infrastructure
├── mcp-testing/          # MCP protocol test fixtures
├── plugins-sdk/          # plugin authoring API
├── plugins/
│   ├── github/
│   ├── slack/
│   ├── notion/
│   └── ...
├── integrations/
│   ├── openai/
│   ├── anthropic/
│   ├── google/
│   └── ...
├── evals/                # evaluation framework + runners
├── cli/                  # developer/operator CLI
└── services/
    ├── api/
    └── worker/
```

Not every package needs to exist initially. The coding agent should create only packages needed by the requested product, while preserving these architectural boundaries.

## Dependency direction

Preferred:

```text
services
   ↓
agents
   ↓
ai / mcp-client / plugins-sdk
   ↓
schemas / core
```

Plugins:

```text
plugin implementation
   ↓
plugins-sdk + schemas + core
```

MCP:

```text
mcp-server
   ↓
plugins-sdk
   ↓
plugin implementation
```

Provider adapters:

```text
integrations/openai
integrations/anthropic
integrations/google
       ↓
       ai
```

Core packages must not depend on concrete provider SDKs, web frameworks, database drivers, or plugin implementations.

## Tooling

- Python: 3.12+; use the newest stable supported version where practical.
- Dependency/project management: uv.
- Workspace: uv workspaces.
- Formatting/linting: Ruff.
- Type checking: ty.
- Tests: pytest.
- Async: asyncio; do not introduce an async framework merely for style.
- HTTP: httpx.
- Schemas/config: Pydantic v2.
- CLI: Typer only if a CLI is actually needed.
- API: FastAPI only where an HTTP service is actually needed.
- Git hooks: Lefthook.
- Commit convention: Conventional Commits.
- Releases: release-please manifest mode.
- CI/CD: GitHub Actions.
- Dependencies: Dependabot.
- Security: CodeQL, dependency review, secret scanning/push protection where available, zizmor.
- Packaging: uv build.
- Publishing: PyPI Trusted Publishing/OIDC.
- Containers: Docker/BuildKit only for deployable services.
- Evals: pytest-compatible evaluation suite; keep provider/network tests explicitly marked.

## What NOT to add

Do not add Poetry, pip-tools, Pipenv, Black, isort, Flake8, tox, pre-commit, or a general-purpose task runner unless there is a concrete repository requirement that cannot be met cleanly with the selected stack.

Do not create a generic `utils` package. Put functionality in a domain package with a clear owner.

## Local command contract

These commands should work from the repository root:

```bash
uv sync
uv run ruff check .
uv run ruff format .
uv run ty check
uv run pytest
uv build
```

Additional commands may be provided for evals and services, but the core commands above must remain stable.
