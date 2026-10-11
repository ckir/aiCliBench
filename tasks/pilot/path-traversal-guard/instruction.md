# Implement Secure Path Traversal Guard

In `path_guard.py`, implement `resolve_sandbox_path(sandbox_root: str | Path, untrusted_path: str) -> Path`.

### Security Requirements:
1. Resolves `untrusted_path` strictly inside `sandbox_root`.
2. Directory Traversal Defense:
   - Detects and rejects path traversal sequences such as `../`, `..\`, nested sequences `....//`, and URL-encoded traversals (`%2e%2e`).
   - If the resolved canonical path falls outside `sandbox_root`, raises `PathTraversalError(f"Path outside sandbox: {untrusted_path}")`.
3. Null-byte injection:
   - Rejects null bytes `\x00` in `untrusted_path`, raising `PathTraversalError`.
4. Symlink escape defense:
   - If a file or directory inside the sandbox is a symlink pointing outside `sandbox_root`, raises `PathTraversalError`.
5. Valid child paths:
   - Returns a canonical `pathlib.Path` inside `sandbox_root`.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
