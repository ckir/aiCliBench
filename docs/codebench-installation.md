# CodeBench installation

Requires Python 3.12+, Git, Docker (Linux containers), and optionally the
`claude` and `agy` CLIs with existing logins.

```bash
uv sync --locked
uv run codebench --help
uv run codebench doctor
```

`doctor` never starts a paid task. It checks Python, Git, Docker, both CLIs
(version/auth readiness where safely detectable), config validity, writable
data dir, image buildability, and adapter output-format support.

Windows: run through WSL2 with Docker. Native Windows sandboxing is out of
scope for v0.1 and not claimed as supported.

Manual smoke test (real CLIs, spends provider credit — never in CI):

```bash
uv run codebench tasks validate example-task
uv run codebench run --task example-task --agents claude --repeat 1
uv run codebench compare --latest
uv run codebench report --latest
```
