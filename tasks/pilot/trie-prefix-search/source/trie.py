"""Prefix Trie for autocomplete."""

from __future__ import annotations


class TrieNode:
    def __init__(self) -> None:
        self.children: dict[str, TrieNode] = {}
        self.is_terminal: bool = False
        self.weight: float = 0.0


class PrefixTrie:
    def __init__(self) -> None:
        self.root = TrieNode()

    def insert(self, word: str, weight: float = 1.0) -> None:
        # Stub
        pass

    def contains(self, word: str) -> bool:
        # Stub
        return False

    def starts_with(self, prefix: str) -> bool:
        # Stub
        return False

    def autocomplete(self, prefix: str, limit: int = 5) -> list[str]:
        # Stub
        return []
