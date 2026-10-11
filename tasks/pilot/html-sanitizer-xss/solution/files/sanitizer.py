"""HTML Sanitizer for XSS protection."""

import html
import re
from html.parser import HTMLParser

_DANGEROUS_TAGS = {"script", "style", "iframe", "object", "embed"}
_URI_ATTRS = {"href", "src", "action", "formaction", "xlink:href", "poster", "cite"}
_SAFE_SCHEMES = {"http", "https", "mailto"}
_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")
_STRIP_RE = re.compile(r"[\x00-\x20\x7f-\x9f]+")


def _is_safe_uri(value: str) -> bool:
    cleaned = _STRIP_RE.sub("", value)
    if cleaned.startswith("//"):
        return False
    match = _SCHEME_RE.match(cleaned)
    if match:
        return match.group(1).lower() in _SAFE_SCHEMES
    # No scheme: a colon before any path/query/fragment delimiter is evasive.
    head = re.split(r"[/?#]", cleaned, maxsplit=1)[0]
    return ":" not in head


class _Sanitizer(HTMLParser):
    def __init__(self, allowed_tags: set[str], allowed_attributes: dict[str, set[str]]) -> None:
        super().__init__(convert_charrefs=True)
        self._allowed_tags = {t.lower() for t in allowed_tags}
        self._allowed_attrs = {
            t.lower(): {a.lower() for a in names} for t, names in allowed_attributes.items()
        }
        self._skip_depth = 0
        self._out: list[str] = []

    def result(self) -> str:
        return "".join(self._out)

    def _render_start(self, tag: str, attrs: list[tuple[str, str | None]], closing: bool) -> str:
        allowed = self._allowed_attrs.get(tag, set())
        parts = [f"<{tag}"]
        for name, value in attrs:
            name = name.lower()
            if name.startswith("on") or name not in allowed:
                continue
            if value is None:
                parts.append(f" {name}")
                continue
            if name in _URI_ATTRS and not _is_safe_uri(value):
                continue
            parts.append(f' {name}="{html.escape(value, quote=True)}"')
        parts.append(" />" if closing else ">")
        return "".join(parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DANGEROUS_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth == 0 and tag in self._allowed_tags:
            self._out.append(self._render_start(tag, attrs, closing=False))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DANGEROUS_TAGS:
            return
        if self._skip_depth == 0 and tag in self._allowed_tags:
            self._out.append(self._render_start(tag, attrs, closing=True))

    def handle_endtag(self, tag: str) -> None:
        if tag in _DANGEROUS_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth == 0 and tag in self._allowed_tags:
            self._out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._out.append(html.escape(data, quote=False))


def sanitize_html(
    html_text: str,
    allowed_tags: set[str] | None = None,
    allowed_attributes: dict[str, set[str]] | None = None,
) -> str:
    parser = _Sanitizer(allowed_tags or set(), allowed_attributes or {})
    parser.feed(html_text)
    parser.close()
    return parser.result()
