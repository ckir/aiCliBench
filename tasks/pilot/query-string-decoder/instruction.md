# Fix URL Query String Decoder

In `qs_decoder.py`, `parse_query_string(qs)` parses a URL query string (without the leading `?`) into a Python dictionary.

Currently, the implementation in `qs_decoder.py`:
1. Fails to convert `+` signs into spaces (e.g. `q=hello+world` should decode to `{"q": "hello world"}`).
2. Overwrites duplicate keys instead of accumulating multiple values into a list (e.g. `tag=a&tag=b` should produce `{"tag": ["a", "b"]}`).
3. Fails when a parameter has no equals sign or empty value (e.g. `flag` or `flag=` should map to `""`).

Fix `parse_query_string` in `qs_decoder.py` so that:
- Keys and values are properly percent-decoded with plus-sign-to-space replacement (`urllib.parse.unquote_plus`).
- If a key appears once, its value is a single string. If it appears multiple times, its value is a list of strings in appearance order.
- Parameters without a value (e.g. `key` or `key=`) have an empty string `""` value.
- Empty or whitespace query strings return an empty dictionary `{}`.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
