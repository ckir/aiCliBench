# Fix the `add` function

`calc.py` defines `add(a, b)` but it returns the wrong result for positive
numbers. For example, `add(2, 3)` should return `5`.

Fix `calc.py` so addition works for integers. Do not modify tests or task
metadata. You can verify with:

```bash
python -m pytest tests/test_visible.py -v
python -c "from calc import add; print(add(2, 3))"
```
