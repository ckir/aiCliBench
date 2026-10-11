"""Streaming newline-delimited JSON parser."""

import json
from collections.abc import Iterable, Iterator
from typing import Any


def parse_ndjson_stream(chunks: Iterable[str]) -> Iterator[Any]:
    """Parse newline-delimited JSON stream chunks.

    Buggy implementation: does not buffer across chunks.
    """
    for chunk in chunks:
        lines = chunk.split("\n")
        for line in lines:
            trimmed = line.strip()
            if trimmed:
                yield json.loads(trimmed)
