"""Hidden acceptance tests for NDJSON Stream Parser."""

from stream_parser import parse_ndjson_stream  # ty: ignore[unresolved-import]


def test_split_across_chunks():
    chunks = ['{"id": 1, "na', 'me": "alpha"}\n{"id": 2}\n']
    results = list(parse_ndjson_stream(chunks))
    assert results == [{"id": 1, "name": "alpha"}, {"id": 2}]


def test_trailing_line_without_newline():
    chunks = ['{"a": 1}\n', '{"b": 2}']
    results = list(parse_ndjson_stream(chunks))
    assert results == [{"a": 1}, {"b": 2}]


def test_blank_lines_and_spaces():
    chunks = ['\n\n{"x": 10}\n   \n', '{"y": 20}\n']
    results = list(parse_ndjson_stream(chunks))
    assert results == [{"x": 10}, {"y": 20}]
