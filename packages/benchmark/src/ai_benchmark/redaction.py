"""Log redaction (§14). Removes common secret patterns; not perfect."""

from __future__ import annotations

import re

_PATTERNS: list[re.Pattern[str]] = [
    # OpenAI-style keys, GitHub tokens, Slack tokens, AWS keys, generic bearer.
    re.compile(r"sk-[A-Za-z0-9-_]{8,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{8,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/=]{8,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[^'\"\s]+['\"]?"),
]

_REPLACEMENT = "***REDACTED***"


def redact_text(text: str) -> tuple[str, bool]:
    """Redact secret-like substrings.

    Returns:
        (redacted_text, redacted_flag).
    """
    redacted = False
    out = text
    for pattern in _PATTERNS:
        out, count = pattern.subn(_REPLACEMENT, out)
        if count:
            redacted = True
    return out, redacted


def redact_bytes(data: bytes) -> tuple[bytes, bool]:
    """Best-effort redaction for byte payloads (UTF-8 with replacement)."""
    text = data.decode("utf-8", errors="replace")
    redacted_text, flag = redact_text(text)
    return redacted_text.encode("utf-8", errors="replace"), flag
