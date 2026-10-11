"""Hidden acceptance tests for PrefixTrie."""

from trie import PrefixTrie  # ty: ignore[unresolved-import]


def test_insert_and_contains():
    trie = PrefixTrie()
    trie.insert("apple", 10.0)
    trie.insert("app", 5.0)
    assert trie.contains("apple")
    assert trie.contains("app")
    assert not trie.contains("appl")
    assert trie.starts_with("appl")


def test_weighted_autocomplete():
    trie = PrefixTrie()
    trie.insert("python", weight=50.0)
    trie.insert("py", weight=10.0)
    trie.insert("pytest", weight=90.0)
    trie.insert("pydantic", weight=90.0)  # tie with pytest -> alphabetical tie-break

    res = trie.autocomplete("py", limit=3)
    # 90.0: pydantic vs pytest (alphabetical: pydantic then pytest)
    # then 50.0: python
    assert res == ["pydantic", "pytest", "python"]
