# Refactor Processors into Onion Middleware Pipeline

In `pipeline.py`, implement an extensible onion-style middleware execution pipeline `Pipeline`.

### Middleware Signature:
`middleware(context: dict, next_fn: Callable[[dict], dict]) -> dict`
Each middleware receives the current mutable or immutable `context` dictionary and a callable `next_fn`. It can inspect/modify the context before calling `next_fn(context)`, and inspect/modify the result returned by `next_fn`.

### Requirements:
1. `use(middleware: Callable) -> Pipeline`:
   - Appends a middleware to the execution chain. Supports method chaining (`return self`).
2. `execute(initial_context: dict) -> dict`:
   - Runs the chain from outermost to innermost.
   - If no middlewares are registered or when the innermost middleware calls `next_fn`, returns the context passed to it.
   - If any middleware raises an exception, the exception propagates cleanly outward through any `try/except` blocks in outer middlewares.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
