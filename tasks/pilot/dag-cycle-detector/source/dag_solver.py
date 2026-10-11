"""DAG Topological sort and cycle detector."""

from __future__ import annotations


class CycleError(Exception):
    def __init__(self, cycle: list[str]) -> None:
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")
        self.cycle = cycle


def topological_sort(dependencies: dict[str, list[str]]) -> list[str]:
    # Stub
    return list(dependencies.keys())


def find_cycle(dependencies: dict[str, list[str]]) -> list[str] | None:
    # Stub
    return None
