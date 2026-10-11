# Implement DAG Topological Sort & Cycle Detection

In `dag_solver.py`, implement dependency graph resolution:

1. `class CycleError(Exception)`:
   - Exception raised when a cycle is detected in a dependency graph.
   - Has attribute `cycle: list[str]` containing the nodes forming the cycle (e.g. `['A', 'B', 'C', 'A']`).

2. `topological_sort(dependencies: dict[str, list[str]]) -> list[str]`:
   - `dependencies` maps a task node to its direct prerequisites (nodes that must run *before* it).
   - Returns a list of node IDs ordered such that every dependency appears before any node that depends on it.
   - Deterministic tie-breaking: when multiple nodes are eligible, order them alphabetically.
   - If the graph contains a cycle, raises `CycleError` with the cycle path.

3. `find_cycle(dependencies: dict[str, list[str]]) -> list[str] | None`:
   - Returns a list of node IDs representing a cycle (e.g. `['A', 'B', 'A']`) if present, or `None` if the graph is a valid DAG.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
