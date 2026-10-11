# Implement Wildcard Event Emitter

In `event_emitter.py`, implement `EventEmitter` for publish-subscribe event routing.

Events are dot-separated topic strings (e.g. `order.created`, `system.auth.login`).

### Requirements:
1. `on(pattern: str, handler: Callable)`:
   - Registers a subscriber callback for a pattern.
   - Patterns support:
     - Exact match: `user.login`
     - Single segment wildcard `*`: `user.*` matches `user.login` and `user.logout`, but NOT `user.profile.update`.
     - Multi-segment wildcard `**`: `system.**` matches `system.start`, `system.auth.login`, `system.core.cpu.high`.
2. `once(pattern: str, handler: Callable)`:
   - Registers a handler that is called only once, then automatically deregistered.
3. `emit(event: str, *args, **kwargs) -> int`:
   - Invokes all matching registered handlers with the passed arguments.
   - Returns the integer count of handlers executed.
4. `off(pattern: str, handler: Callable) -> bool`:
   - Deregisters `handler` from `pattern`. Returns `True` if found and removed, `False` otherwise.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
