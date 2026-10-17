# Changelog

## [0.2.0](https://github.com/ckir/aiCliBench/compare/ai-cli-v0.1.0...ai-cli-v0.2.0) (2026-10-17)


### Features

* **benchmark:** deterministic task repo materialization with pinned-commit check ([12578d2](https://github.com/ckir/aiCliBench/commit/12578d2f96afe22293df476ca39f48e0d6e96ad5))
* **benchmark:** report quality-gate counts separately from acceptance ([2761bfa](https://github.com/ckir/aiCliBench/commit/2761bfa6a4002ed2f5b887b9be48bfaa76cbfe59))
* **benchmark:** Wilson intervals, exact sign test and paired bootstrap for pass rates ([6931b52](https://github.com/ckir/aiCliBench/commit/6931b525aabbee7ba51dbeb20b9e97432d79c84e))
* **cli:** add `codebench tasks build` to pre-build task images ([9c5faf0](https://github.com/ckir/aiCliBench/commit/9c5faf0cc7205af8ea9ce9063367d86f02f85116))
* **cli:** tasks init scaffolds a verifiable task ([63f91c3](https://github.com/ckir/aiCliBench/commit/63f91c3a5b40c3eeabb148b2a65fd70d94ee72bc))
* **codebench:** implement CodeBench Local MVP v0.1.0 ([89924a0](https://github.com/ckir/aiCliBench/commit/89924a00264a75a58b04f7822b16d07449b2d8ac))
* implement vertical-slice monorepo (core, ai, mcp, plugins, agents, evals, services) ([5196cae](https://github.com/ckir/aiCliBench/commit/5196cae521db871077394083e8430be36bc13993))
* **integrations:** generic CLI agent adapter configurable via [agents.custom.&lt;name&gt;] ([1ed6b82](https://github.com/ckir/aiCliBench/commit/1ed6b822b74eea2ff0bfbbfd93e2f28e4466e9a6))


### Bug Fixes

* **cli:** strip ANSI escapes in tasks build help test ([f851065](https://github.com/ckir/aiCliBench/commit/f85106511700df62109c5627e9b68871275780a1))
* **codebench:** green gate, provenance manifest completeness, generic adapter argv from config only ([f24fdd7](https://github.com/ckir/aiCliBench/commit/f24fdd7152b048fa69ce7812eed64f591ccf4bbf))
