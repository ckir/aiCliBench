"""Hidden acceptance tests for DAG Solver."""

import pytest
from dag_solver import CycleError, find_cycle, topological_sort  # ty: ignore[unresolved-import]


def test_topological_sort_valid_dag():
    # task depends on:
    deps = {
        "build": ["compile", "lint"],
        "compile": [],
        "lint": [],
        "test": ["build"],
    }
    order = topological_sort(deps)
    # compile and lint must precede build; build must precede test
    assert order.index("compile") < order.index("build")
    assert order.index("lint") < order.index("build")
    assert order.index("build") < order.index("test")
    # Alphabetical tie-breaking: lint vs compile
    assert order == ["compile", "lint", "build", "test"]


def test_cycle_detection():
    deps = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"],
    }
    assert find_cycle(deps) is not None
    with pytest.raises(CycleError) as exc_info:
        topological_sort(deps)
    cycle = exc_info.value.cycle
    assert cycle[0] == cycle[-1]  # Closed loop
