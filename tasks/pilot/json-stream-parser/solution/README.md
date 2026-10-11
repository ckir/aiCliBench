# Solution

Buffer incomplete chunks:
```python
def parse_ndjson_stream(chunks: Iterable[str]) -> Iterator[Any]:
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        lines = buffer.split("\n")
        # Keep the last segment in buffer (it may be incomplete)
        buffer = lines.pop()
        for line in lines:
            trimmed = line.strip()
            if trimmed:
                yield json.loads(trimmed)
    if buffer.strip():
        yield json.loads(buffer.strip())
```
