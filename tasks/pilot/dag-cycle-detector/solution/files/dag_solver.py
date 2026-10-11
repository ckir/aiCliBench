"""DAG Topological sort and cycle detector."""

from __future__ import annotations

import heapq


class CycleError(Exception):
    def __init__(self, cycle: list[str]) -> None:
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")
        self.cycle = cycle


def _all_nodes(dependencies: dict[str, list[str]]) -> set[str]:
    nodes = set(dependencies)
    for deps in dependencies.values():
        nodes.update(deps)
    return nodes


def topological_sort(dependencies: dict[str, list[str]]) -> list[str]:
    nodes = _all_nodes(dependencies)
    indegree = dict.fromkeys(nodes, 0)
    dependents: dict[str, list[str]] = {n: [] for n in nodes}
    for node, deps in dependencies.items():
        for dep in set(deps):
            indegree[node] += 1
            dependents[dep].append(node)

    ready = [n for n, d in indegree.items() if d == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for nxt in dependents[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                heapq.heappush(ready, nxt)

    if len(order) != len(nodes):
        cycle = find_cycle(dependencies)
        raise CycleError(cycle if cycle is not None else [])
    return order


def find_cycle(dependencies: dict[str, list[str]]) -> list[str] | None:
    white, gray, black = 0, 1, 2
    color = dict.fromkeys(_all_nodes(dependencies), white)
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = gray
        stack.append(node)
        for dep in sorted(dependencies.get(node, [])):
            if color[dep] == gray:
                return [*stack[stack.index(dep) :], dep]
            if color[dep] == white:
                found = visit(dep)
                if found is not None:
                    return found
        stack.pop()
        color[node] = black
        return None

    for start in sorted(color):
        if color[start] == white:
            found = visit(start)
            if found is not None:
                return found
    return None
