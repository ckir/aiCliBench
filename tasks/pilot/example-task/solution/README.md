# Reference solution (for validators, never shown to agents)

The bug is in `calc.py`: `add` subtracts. The fix:

```python
def add(a, b):
    return a + b
```

Validation procedure:

1. Generate the demo repo from `source/` with fixed git identity/dates.
2. Confirm the starting commit fails `evaluator/run_tests.sh`.
3. Apply the fix above.
4. Confirm `evaluator/run_tests.sh` exits 0.
