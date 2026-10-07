# Contributing

## Setup

```bash
uv sync
```

## Quality

```bash
uv run ruff check .
uv run ruff format .
uv run ty check
uv run pytest
```

## Evals

Deterministic evals:

```bash
uv run pytest -m eval
```

Live provider evals should be explicitly configured and should not run on untrusted pull requests.

## Commits

Use Conventional Commits:

```text
feat(plugin): add calendar search
fix(mcp): validate tool arguments
feat(ai)!: remove legacy model interface
chore: update dependencies
```

## Adding a plugin

Read `docs/ADDING_A_PLUGIN.md`.

## Adding an AI provider

Read `docs/ADDING_AN_AI_PROVIDER.md`.

## Adding an MCP tool

Read `docs/ADDING_AN_MCP_TOOL.md`.

## Releases

Releases are owned by release-please in manifest mode
(`release-please-config.json`, `.release-please-manifest.json`).
Each package versions independently; a package with no changes gets no
version bump. Do not edit versions or changelogs by hand — merging to `main`
may open release PRs that do that work.

## Publishing

`.github/workflows/publish.yml` runs on GitHub releases, builds every
package (`uv build --all-packages`), and publishes to PyPI via Trusted
Publishing (OIDC, `id-token: write`). No long-lived API tokens are used.
One-time human setup: register each PyPI project with this repository as a
trusted publisher and create the release environment.

## Secrets

Secrets come from environment variables; `.env.example` lists the names with
safe placeholders only. Local `.env` files are gitignored — never commit
credentials, and never log secrets, API keys, authorization headers, or full
provider responses. Tests must not depend on production credentials.
Live-provider tests and evals (`-m live`) require real keys and run only in
scheduled or manually dispatched workflows, never on untrusted pull requests.
