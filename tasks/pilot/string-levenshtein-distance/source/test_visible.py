from levenshtein import levenshtein_distance


def test_short_words():
    assert levenshtein_distance("kitten", "sitting") == 3
