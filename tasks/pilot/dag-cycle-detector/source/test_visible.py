from dag_solver import CycleError


def test_cycle_error():
    err = CycleError(["A", "B", "A"])
    assert err.cycle == ["A", "B", "A"]
