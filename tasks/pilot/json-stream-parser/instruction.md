# Fix Streaming NDJSON Parser

In `stream_parser.py`, `parse_ndjson_stream(chunks)` reads an iterable of string chunks representing newline-delimited JSON (NDJSON) and yields parsed JSON objects.

Currently, the implementation naively splits each chunk by `\n` independently, which breaks whenever a JSON record spans across chunk boundaries (for example, when a chunk ends in the middle of a JSON string or object).

Fix `stream_parser.py` so that:
1. Partial lines across chunk boundaries are correctly buffered until a full newline `\n` is encountered.
2. Any trailing buffered line after the final chunk is parsed if non-empty.
3. Blank lines (e.g. empty lines or whitespace-only) between records are skipped.
4. Each valid record is yielded as a parsed Python dictionary/value.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
