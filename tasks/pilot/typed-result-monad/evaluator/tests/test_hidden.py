"""Hidden acceptance tests for Result Monad."""

import pytest
from result import Err, Ok, UnwrapError  # ty: ignore[unresolved-import]


def test_ok_operations():
    ok = Ok(10)
    assert ok.is_ok()
    assert not ok.is_err()
    assert ok.unwrap() == 10
    assert ok.unwrap_or(0) == 10

    mapped = ok.map(lambda x: x * 2)
    assert mapped.is_ok()
    assert mapped.unwrap() == 20

    chained = ok.and_then(lambda x: Ok(f"num: {x}"))
    assert chained.unwrap() == "num: 10"


def test_err_operations():
    err = Err("database timeout")
    assert not err.is_ok()
    assert err.is_err()

    with pytest.raises(UnwrapError):
        err.unwrap()

    assert err.unwrap_or("default") == "default"

    # map is a no-op on Err
    mapped = err.map(lambda x: x * 2)
    assert mapped.is_err()

    # map_err transforms error
    transformed = err.map_err(lambda msg: f"Error: {msg}")
    assert transformed.is_err()
