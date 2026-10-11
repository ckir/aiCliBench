# Implement Prefix Trie with Weighted Autocomplete

In `trie.py`, implement the `PrefixTrie` class.

### Requirements:
1. `insert(word: str, weight: float = 1.0) -> None`:
   - Inserts `word` into the trie. If `word` already exists, updates its weight to `weight`.
2. `contains(word: str) -> bool`:
   - Returns `True` if `word` exists as an inserted term, `False` otherwise.
3. `starts_with(prefix: str) -> bool`:
   - Returns `True` if any inserted word starts with `prefix`.
4. `autocomplete(prefix: str, limit: int = 5) -> list[str]`:
   - Returns up to `limit` words starting with `prefix`.
   - Results must be sorted primarily by `weight` descending, and secondarily alphabetically by word ascending for ties.
   - If `prefix` is empty `""`, returns top weighted words in the trie.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
