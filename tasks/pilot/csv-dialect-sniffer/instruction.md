# Implement CSV Delimiter Sniffer & Parser

In `csv_sniffer.py`, implement two functions:

1. `sniff_delimiter(sample: str, candidates: tuple[str, ...] = (",", "\t", ";", "|")) -> str`:
   - Inspects `sample` (first few lines of tabular text) and determines the most likely column delimiter from `candidates`.
   - The selected delimiter should produce consistent column counts across lines.
   - Defaults to `","` if indeterminate.

2. `parse_tabular_data(text: str, delimiter: str | None = None) -> list[dict[str, str]]`:
   - If `delimiter` is not provided, uses `sniff_delimiter` on the text.
   - Parses the text into a list of row dictionaries mapping header name to string value.
   - Accurately handles double-quoted fields containing the delimiter or escaped quotes (`""`).
   - Ignores trailing empty lines.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
