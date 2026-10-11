# Solution

```python
def parse_query_string(qs: str) -> dict[str, Any]:
    if not qs or not qs.strip():
        return {}
    raw_res: dict[str, list[str]] = {}
    for part in qs.split("&"):
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
        else:
            k, v = part, ""
        key = urllib.parse.unquote_plus(k)
        val = urllib.parse.unquote_plus(v)
        raw_res.setdefault(key, []).append(val)
    return {k: v[0] if len(v) == 1 else v for k, v in raw_res.items()}
```
