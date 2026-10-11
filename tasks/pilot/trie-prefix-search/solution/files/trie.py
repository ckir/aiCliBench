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
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_terminal = True
        if weight > node.weight:
            node.weight = weight

    def contains(self, word: str) -> bool:
        node = self.root
        for ch in word:
            if ch not in node.children:
                return False
            node = node.children[ch]
        return node.is_terminal

    def starts_with(self, prefix: str) -> bool:
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return False
            node = node.children[ch]
        return True

    def autocomplete(self, prefix: str, limit: int = 5) -> list[str]:
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return []
            node = node.children[ch]

        results: list[tuple[float, str]] = []

        def dfs(n: TrieNode, path: str) -> None:
            if n.is_terminal:
                results.append((-n.weight, path))
            for ch, child in n.children.items():
                dfs(child, path + ch)

        dfs(node, prefix)
        results.sort()
        return [word for _, word in results[:limit]]