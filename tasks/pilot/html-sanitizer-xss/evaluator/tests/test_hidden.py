"""Hidden acceptance tests for HTML Sanitizer."""

from sanitizer import sanitize_html  # ty: ignore[unresolved-import]


def test_strips_script_and_contents():
    payload = '<p>Hello <script>alert("XSS")</script>World</p>'
    res = sanitize_html(payload, allowed_tags={"p"})
    assert "<script>" not in res
    assert "alert" not in res
    assert res == "<p>Hello World</p>"


def test_strips_javascript_href_and_event_handlers():
    payload = '<a href="javascript:alert(1)" onclick="steal()" title="click">link</a>'
    res = sanitize_html(
        payload,
        allowed_tags={"a"},
        allowed_attributes={"a": {"href", "title"}},
    )
    assert "javascript:" not in res
    assert "onclick" not in res
    assert "steal" not in res
    assert '<a title="click">link</a>' in res
