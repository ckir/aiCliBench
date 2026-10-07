# Agent Handoff / Implementation Plan

## Phase 0 — Ask/resolve product facts

Before implementation, identify:
- repository/package name;
- GitHub owner/repository;
- Python versions;
- which packages are actually required;
- whether packages publish to PyPI;
- whether services deploy to containers;
- deployment target;
- supported AI providers;
- required MCP SDK/version;
- plugin list;
- authentication requirements.

If these are unknown, use conservative placeholders and document them. Do not invent production credentials or infrastructure.

## Phase 1 — Workspace bootstrap

Create:
- root `pyproject.toml`;
- uv workspace;
- `.python-version`;
- `uv.lock`;
- source-layout packages;
- package-level `pyproject.toml`;
- package tests;
- package READMEs.

Each distributable package must be independently buildable.

Acceptance:

```bash
uv sync --locked
uv build
```

## Phase 2 — Foundation

Implement `core` and `schemas`.

Acceptance:
- no provider SDK imports;
- no network calls;
- strong tests;
- public APIs typed.

## Phase 3 — AI abstraction

Implement only abstractions actually required by the application.

Provide a fake/test implementation.

Acceptance:
- production code can be tested without network access;
- provider SDK types do not escape adapters;
- structured outputs are validated.

## Phase 4 — Provider adapters

Implement requested providers as separate packages.

Each provider adapter needs:
- configuration;
- client lifecycle;
- timeout;
- error normalization;
- request correlation where supported;
- tests with mocked transport;
- explicit live tests if desired.

Never require provider credentials for normal unit tests.

## Phase 5 — Plugin SDK

Define:
- plugin metadata;
- capability/tool specification;
- configuration declaration;
- authorization metadata;
- invocation interface;
- optional lifecycle.

Keep it minimal.

Example conceptual interface:

```python
class Plugin(Protocol):
    @property
    def metadata(self) -> PluginMetadata: ...

    def tools(self) -> Sequence[ToolSpec]: ...
```

Tool specifications should have stable:
- name;
- description;
- input schema;
- output schema;
- side-effect classification.

## Phase 6 — Concrete plugins

Implement requested plugins.

Every plugin gets:
- independent package;
- tests;
- fake client;
- integration tests;
- README;
- configuration documentation;
- security notes for scopes/permissions;
- release metadata.

A plugin must remain usable independently of MCP.

## Phase 7 — MCP

Implement:
- server adapter;
- client;
- test harness.

MCP server should discover plugin capabilities and expose them as MCP tools without duplicating business logic.

Test:
- server startup;
- capability discovery;
- tool discovery;
- valid invocation;
- invalid arguments;
- authorization rejection;
- downstream failure;
- timeout behavior.

## Phase 8 — Agents

Implement runtime only after tool/plugin contracts are stable.

Agent runtime should support:
- model abstraction;
- tool registry;
- execution budget;
- timeout;
- max tool calls/steps;
- authorization;
- structured result;
- deterministic fake-model tests.

Do not let the model directly execute arbitrary code.

## Phase 9 — Evals

Create:
- deterministic evaluation cases;
- provider-independent fake-model tests;
- optional live-provider suite;
- regression dataset format;
- evaluation reporting.

PR CI must remain deterministic unless explicitly configured otherwise.

Schedule live evals separately.

## Phase 10 — Services

For each service:
- thin application composition layer;
- health endpoint where applicable;
- structured logging;
- graceful shutdown;
- configuration validation;
- Dockerfile only if deployment requires it.

## Phase 11 — Developer automation

Configure:
- Ruff;
- ty;
- pytest;
- Lefthook;
- Conventional Commit validation.

Local hooks should be fast.

## Phase 12 — CI

PR:
- lockfile verification;
- lint;
- format;
- types;
- tests;
- package builds.

Main:
- same checks;
- optional integration suite.

Nightly/scheduled:
- live provider tests;
- security scans;
- dependency checks where useful.

## Phase 13 — Release

Configure release-please manifest mode.

Independent package releases should be possible.

A package with no changes must not receive a pointless version bump.

## Phase 14 — Publishing

Configure:
- PyPI Trusted Publishers;
- release environment;
- OIDC;
- package publishing;
- provenance/attestations where supported.

The agent must document manual PyPI/GitHub configuration steps.

## Phase 15 — Security hardening

Review:
- GitHub token permissions;
- action SHA pinning;
- secrets;
- dependency review;
- CodeQL;
- Dependabot;
- zizmor;
- Docker image permissions;
- plugin OAuth scopes;
- MCP tool authorization.

## Final acceptance

The implementation is complete only when:

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
uv build
```

all pass.

Also verify that the following are understandable to a new contributor:

```text
How do I add a plugin?
How do I add an MCP tool?
How do I add an AI provider?
How do I run tests?
How do I run evals?
How does a release happen?
How does a package get published?
Where are secrets configured?
```
