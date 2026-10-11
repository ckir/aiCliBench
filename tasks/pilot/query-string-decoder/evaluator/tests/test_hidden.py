"""Hidden acceptance tests for Query String Decoder."""

from qs_decoder import parse_query_string  # ty: ignore[unresolved-import]


def test_plus_sign_and_percent_encoding():
    qs = "q=hello+world%21&user=john%2Bdoe"
    res = parse_query_string(qs)
    assert res == {"q": "hello world!", "user": "john+doe"}


def test_repeated_keys_accumulate_list():
    qs = "filter=active&tag=python&tag=async&tag=ai"
    res = parse_query_string(qs)
    assert res == {"filter": "active", "tag": ["python", "async", "ai"]}


def test_empty_value_and_key_only():
    qs = "debug&verbose=&dry_run"
    res = parse_query_string(qs)
    assert res == {"debug": "", "verbose": "", "dry_run": ""}
