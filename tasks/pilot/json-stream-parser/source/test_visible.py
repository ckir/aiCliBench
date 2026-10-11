from stream_parser import parse_ndjson_stream


def test_single_complete_chunk():
    chunks = ['{"id": 1}\n{"id": 2}\n']
    results = list(parse_ndjson_stream(chunks))
    assert results == [{"id": 1}, {"id": 2}]
