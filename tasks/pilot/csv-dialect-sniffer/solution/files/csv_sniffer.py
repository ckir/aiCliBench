"""CSV dialect sniffer and parser."""

import csv
from io import StringIO


def sniff_delimiter(sample: str, candidates: tuple[str, ...] = (",", "\t", ";", "|")) -> str:
    """Detect the delimiter from a sample of CSV text."""
    # Try each candidate delimiter
    for delim in candidates:
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=delim)
            if dialect.delimiter == delim:
                return delim
        except csv.Error:
            continue
    # Fallback: try first line only (header)
    first_line = sample.split("\n")[0] if sample else ""
    if first_line:
        for delim in candidates:
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(first_line, delimiters=delim)
                if dialect.delimiter == delim:
                    return delim
            except csv.Error:
                continue
    # Fallback: use csv.Sniffer without delimiter restriction
    try:
        dialect = csv.Sniffer().sniff(sample)
        return dialect.delimiter
    except csv.Error:
        pass
    # Default to comma
    return ","


def parse_tabular_data(text: str, delimiter: str | None = None) -> list[dict[str, str]]:
    """Parse CSV text into a list of dictionaries."""
    if not text.strip():
        return []

    # Sniff delimiter if not provided
    if delimiter is None:
        delimiter = sniff_delimiter(text)

    # Parse CSV
    reader = csv.DictReader(StringIO(text), delimiter=delimiter)
    rows = []
    for row in reader:
        # Convert all values to strings
        str_row = {k: str(v) for k, v in row.items()}
        rows.append(str_row)
    return rows
