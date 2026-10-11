# Solution

Helper to compare prerelease identifiers:
```python
def _compare_identifier(a: str, b: str) -> int:
    a_num, b_num = a.isdigit(), b.isdigit()
    if a_num and b_num:
        return int(a) - int(b)
    if a_num and not b_num:
        return -1
    if not a_num and b_num:
        return 1
    return (a > b) - (a < b)
```
