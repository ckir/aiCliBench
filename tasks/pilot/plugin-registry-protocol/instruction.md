# Refactor Plugin Registry to typing.Protocol

In `plugin_loader.py`, implement a flexible plugin registration and dispatch system.

### Protocol Specification:
Define `@runtime_checkable class Plugin(Protocol)`:
- `@property def name(self) -> str: ...`
- `@property def priority(self) -> int: ...` (lower integer = executed earlier)
- `def process(self, data: dict) -> dict: ...`

### Registry Requirements:
`PluginRegistry`:
1. `register(plugin: Any) -> None`:
   - Validates that `plugin` conforms to the `Plugin` protocol (has `name`, `priority`, `process`). If not, raises `TypeError`.
   - Prevents duplicate registration of the same plugin `name` by raising `ValueError`.
2. `unregister(name: str) -> bool`:
   - Removes plugin by name. Returns `True` if removed, `False` if not found.
3. `get_plugins() -> list[Plugin]`:
   - Returns all registered plugins sorted by `priority` ascending.
4. `run_pipeline(data: dict) -> dict`:
   - Feeds `data` sequentially through each plugin's `process(data)` method in ascending priority order.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
