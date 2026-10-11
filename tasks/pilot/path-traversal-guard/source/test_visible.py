from path_guard import PathTraversalError


def test_error_defined():
    assert issubclass(PathTraversalError, Exception)
