# CodeBench safety

Release-blocking requirements:

- Separate container invocations for agent phase and evaluation phase.
- Agent container: only the workspace + tmp writable; read-only rootfs where
  supported; CPU/memory/PIDs limits; non-root user; dropped capabilities;
  `no-new-privileges`; no privileged mode; explicit mounts only.
- Never mount the Docker socket, home directory, provider credential
  directories wholesale, hidden tests, evaluator scripts, or reference
  solutions into the agent phase.
- If a provider CLI needs auth files, mount the minimum read-only material,
  document the exposure, and never copy it into artifacts. When unsafe, refuse
  the run with a fail-closed diagnostic — never fall back to unrestricted host
  execution.
- Default network disabled for agents; per-task opt-in recorded and reported
  separately.
- Subprocesses use argument lists only; prompts passed safely (quotes,
  Unicode, shell metacharacters covered by tests).
- Task-relative paths validated against traversal/symlink escapes.
- Logs redacted for common token patterns (best effort; perfect redaction not
  claimed). Secrets never logged; full env never dumped.
- `workspace_cleanup = "retain"` by default under the data dir;
  `codebench runs clean` requires `--confirm --no-dry-run` and only touches
  the data dir. Source repos and arbitrary paths are never deleted.
- Ctrl+C terminates the active container/process, marks the run
  `interrupted`, saves artifacts, and exits cleanly (exit 130).
- The evaluator runs the trusted command in a fresh container without provider
  credentials; agent self-reports are informational only.
