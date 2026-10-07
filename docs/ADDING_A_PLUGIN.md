# Adding a Plugin

A plugin is a separately packaged capability provider.

## Steps

1. Create `packages/plugins/<name>`.
2. Add `pyproject.toml`.
3. Put implementation under `src/<package_name>/`.
4. Implement the plugin SDK contract.
5. Define explicit tool schemas.
6. Classify each tool as read/write/destructive.
7. Add a fake client.
8. Add unit tests.
9. Add integration tests.
10. Add documentation.
11. Add release metadata to release-please.
12. Add any required secret/configuration documentation.

## Design rule

Do not implement MCP handlers inside the plugin.

Instead:

```text
Plugin
  |
  +-- tool implementation
       |
       +-- direct Python use
       +-- Agent registry
       +-- MCP adapter
```
