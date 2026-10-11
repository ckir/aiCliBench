"""URL Query String Decoder."""

import urllib.parse
from typing import Any


def parse_query_string(qs: str) -> dict[str, Any]:
    """Parse query string.

    Buggy: overwrites duplicates, does not unquote plus.
    """
    if not qs or not qs.strip():
        return {}
    res: dict[str, Any] = {}
    for part in qs.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            # BUG: uses unquote instead of unquote_plus, overwrites keys
            res[urllib.parse.unquote(k)] = urllib.parse.unquote(v)
        else:
            res[urllib.parse.unquote(part)] = ""
    return res
