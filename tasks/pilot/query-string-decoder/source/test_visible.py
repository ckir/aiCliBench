from qs_decoder import parse_query_string


def test_simple_kv():
    assert parse_query_string("name=alice&age=30") == {"name": "alice", "age": "30"}
