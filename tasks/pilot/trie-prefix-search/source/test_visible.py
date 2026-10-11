from trie import PrefixTrie


def test_trie_instantiation():
    trie = PrefixTrie()
    assert trie.contains("anything") is False
