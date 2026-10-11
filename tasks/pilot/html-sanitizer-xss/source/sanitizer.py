"""HTML Sanitizer for XSS protection."""


def sanitize_html(
    html_text: str,
    allowed_tags: set[str] | None = None,
    allowed_attributes: dict[str, set[str]] | None = None,
) -> str:
    # Stub: naive pass-through (insecure)
    return html_text
