from result import Err, Ok


def test_basic_types():
    assert Ok(1).value == 1
    assert Err("error").error == "error"
