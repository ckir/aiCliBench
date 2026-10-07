# Architecture

## 1. Package taxonomy

### `core`

Stable, provider-independent domain primitives.

Examples:
- IDs;
- errors;
- result types;
- capability metadata;
- small shared utilities with a clear domain owner.

It should be one of the most dependency-light packages.

### `schemas`

Shared Pydantic models and JSON-compatible contracts.

Rules:
- no provider SDK dependencies;
- no database dependencies;
- no network access.

### `ai`

Product-level model abstraction.

Possible concepts:
- `Model`
- `ChatModel`
- `GenerationRequest`
- `GenerationResult`
- `ToolCall`
- `Usage`
- structured-output interfaces

Keep it intentionally small.

### `integrations/*`

Concrete provider adapters.

Examples:
- `integrations/openai`
- `integrations/anthropic`
- `integrations/google`

Provider-specific SDKs stay here.

### `agents`

Agent runtime/orchestration.

Responsibilities:
- planning/execution loop;
- tool selection;
- conversation state;
- budgets/timeouts;
- tool authorization;
- tracing hooks.

Do not embed provider-specific SDK calls directly into the runtime.

### `plugins-sdk`

Plugin contract.

A plugin should be able to provide:
- metadata;
- tools;
- optional resources/prompts;
- configuration requirements;
- lifecycle hooks if genuinely necessary.

### `plugins/*`

Concrete integrations exposed as reusable capabilities.

Example:

```text
plugins/github
  GitHubPlugin
    ├── search_repositories
    ├── get_issue
    ├── create_issue
    └── ...
```

The plugin must not require MCP to be useful.

### `mcp-core`

MCP-neutral concepts and shared adapters.

### `mcp-server`

Maps plugin/tool capabilities into MCP server endpoints/transports.

The server is an adapter around plugin capabilities.

### `mcp-client`

Client abstraction for connecting to remote MCP servers.

Keep transport/provider details behind interfaces.

### `mcp-testing`

Reusable test harnesses:
- discovery;
- tool schema validation;
- invocation;
- malformed input;
- transport errors.

### `evals`

Evaluation infrastructure.

Keep datasets and evaluation runners separate from production package code.

### `services`

Deployable applications.

Examples:
- API;
- worker;
- webhook receiver;
- MCP gateway.

Services compose packages. They should contain very little domain logic.

## 2. Plugin lifecycle

Desired model:

```text
Plugin metadata
     |
     v
Plugin capabilities
     |
     +----> direct Python caller
     |
     +----> agent tool registry
     |
     +----> MCP adapter
     |
     +----> CLI adapter (optional)
```

This prevents MCP from becoming the application's internal architecture.

## 3. Provider lifecycle

```text
Agent
  |
  v
AI abstraction
  |
  +--> OpenAI adapter
  +--> Anthropic adapter
  +--> Google adapter
  +--> fake/test adapter
```

Provider-specific retries, request IDs, SDK errors, and serialization belong in the adapter.

## 4. Side effects

Every side-effecting capability should have a clear boundary.

Classify tools as:

- `read`
- `write`
- `destructive`

A write/destructive tool should be explicitly authorized by the caller/runtime.

## 5. Observability

Do not hardwire one telemetry vendor into every package.

Define narrow hooks/interfaces where observability is needed.

Services can install:
- logging;
- metrics;
- tracing;
- provider request correlation.

Avoid logging prompts/responses by default when they may contain user-sensitive data.

## 6. Persistence

Do not add a database dependency to core packages.

Database access belongs in:
- a persistence package;
- a service;
- or a concrete integration.

Use repositories/interfaces if multiple backends genuinely need to be supported.

## 7. Dependency rules

Use one-way dependencies.

A useful check is:

```text
core       -> nothing application-specific
schemas    -> core
ai         -> core, schemas
integrations/* -> ai, schemas, core
plugins-sdk   -> core, schemas
plugins/*     -> plugins-sdk, integrations, schemas, core
mcp-*         -> plugins-sdk, schemas, core
agents        -> ai, plugins-sdk, mcp-client, schemas, core
services      -> everything required to compose the product
evals         -> public packages + test infrastructure
```

If a dependency violates this direction, stop and reconsider the boundary.
