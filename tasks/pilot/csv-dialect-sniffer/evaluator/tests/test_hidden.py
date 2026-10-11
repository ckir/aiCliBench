"""Hidden acceptance tests for CSV Sniffer."""

from csv_sniffer import parse_tabular_data, sniff_delimiter  # ty: ignore[unresolved-import]


def test_tab_and_semicolon_detection():
    tsv = "name\tage\tcity\nAlice\t30\nLondon\nBob\t25\tParis"
    assert sniff_delimiter(tsv) == "\t"

    scv = "id;item;price\n1;widget;9.99\n2;gear;14.50"
    assert sniff_delimiter(scv) == ";"


def test_parse_with_quotes_and_escapes():
    data = 'name,notes,score\n"Doe, John","Very ""good"" result",95\nAlice,Normal,100'
    rows = parse_tabular_data(data)
    assert len(rows) == 2
    assert rows[0]["name"] == "Doe, John"
    assert rows[0]["notes"] == 'Very "good" result'
    assert rows[0]["score"] == "95"
    assert rows[1]["name"] == "Alice"
