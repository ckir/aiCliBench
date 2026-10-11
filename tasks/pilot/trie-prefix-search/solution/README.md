# Reference Solution for trie-prefix-search

This directory contains the complete implementation of the PrefixTrie class.

## Files

- `trie.py` - Complete implementation of the PrefixTrie with:
  - `TrieNode` class with children dictionary, terminal flag, and weight
  - `PrefixTrie` class with:
    - `insert(word, weight)` - Insert word with weight
    - `contains(word)` - Check if word exists
    - `starts_with(prefix)` - Check if any word starts with prefix
    - `autocomplete(prefix, limit)` - Return top weighted completions