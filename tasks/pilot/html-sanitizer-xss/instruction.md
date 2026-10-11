# Sanitize HTML Content to Prevent XSS

In `sanitizer.py`, implement `sanitize_html(html: str, allowed_tags: set[str], allowed_attributes: dict[str, set[str]]) -> str` using Python's standard `html.parser.HTMLParser`.

### Requirements:
1. Strips dangerous tags entirely (including `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`) and removes their inner text content.
2. Only tags in `allowed_tags` (e.g. `{'b', 'i', 'p', 'a', 'strong'}`) are retained. Any other tag is stripped, but its text content is preserved.
3. For retained tags, only attributes specified in `allowed_attributes[tag]` are kept.
4. URI attributes (such as `href` on `<a>` or `src` on `<img>`):
   - Only `http:`, `https:`, and `mailto:` schemes or relative paths are permitted.
   - Any `javascript:`, `data:`, `vbscript:`, or protocol-relative/evasive schemes must be stripped.
5. All inline event handlers (`onclick`, `onerror`, `onload`, `onmouseover`, etc.) must be strictly stripped.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
