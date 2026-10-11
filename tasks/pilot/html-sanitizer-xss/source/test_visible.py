from sanitizer import sanitize_html


def test_plain_text():
    assert sanitize_html("hello world") == "hello world"
