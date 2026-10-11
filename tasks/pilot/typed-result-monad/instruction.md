# Implement Typed Result Monad

In `result.py`, implement a Rust-inspired typed `Result[T, E]` algebraic data type (`Ok[T]` and `Err[E]`).

### Requirements:
1. `class UnwrapError(Exception)`
2. `Ok[T]` and `Err[E]`:
   - `Ok(value: T)`: creates a successful result containing `value`.
   - `Err(error: E)`: creates an error result containing `error`.
   - Both inherit from / implement `Result[T, E]`.
3. Methods on `Result`:
   - `is_ok() -> bool`: `True` for `Ok`, `False` for `Err`.
   - `is_err() -> bool`: `True` for `Err`, `False` for `Ok`.
   - `unwrap() -> T`: returns `value` for `Ok`. Raises `UnwrapError` containing error context for `Err`.
   - `unwrap_or(default: T) -> T`: returns `value` for `Ok`, `default` for `Err`.
   - `map(fn: Callable[[T], U]) -> Result[U, E]`: applies `fn` to inner value if `Ok`, otherwise returns `self`.
   - `map_err(fn: Callable[[E], F]) -> Result[T, F]`: applies `fn` to error if `Err`, otherwise returns `self`.
   - `and_then(fn: Callable[[T], Result[U, E]]) -> Result[U, E]`: monadic bind / flatMap. Calls `fn` with inner value if `Ok`, otherwise returns `self`.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
