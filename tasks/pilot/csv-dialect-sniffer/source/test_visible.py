from csv_sniffer import sniff_delimiter


def test_default_delimiter():
    assert sniff_delimiter("a,b,c\n1,2,3") == ","
