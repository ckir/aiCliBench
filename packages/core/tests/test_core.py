from ai_core import (
    AuthorizationError,
    ConfigurationError,
    OperationTimeoutError,
    ProviderError,
    Result,
    ToolExecutionError,
    ValidationError,
    is_valid_id,
    new_id,
)


def test_core_package_imports():
    import ai_core

    assert ai_core is not None


def test_new_id_unique_and_prefixed():
    first = new_id("req")
    second = new_id("req")

    assert first != second
    assert first.startswith("req_")
    assert is_valid_id(first)
    assert is_valid_id("abc123")
    assert not is_valid_id("")


def test_result_ok_and_err():
    ok: Result[int] = Result(value=1)
    assert ok.is_ok
    assert ok.unwrap() == 1

    err = Result[int](error=ValidationError("bad"))
    assert not err.is_ok
    try:
        err.unwrap()
    except ValidationError:
        pass
    else:
        raise AssertionError("expected ValidationError")


def test_error_hierarchy_preserves_context():
    assert issubclass(ConfigurationError, Exception)
    assert issubclass(ValidationError, Exception)
    assert issubclass(AuthorizationError, Exception)
    assert issubclass(ToolExecutionError, Exception)
    assert issubclass(ProviderError, Exception)
    assert issubclass(OperationTimeoutError, Exception)

    exc = ProviderError("boom", provider="openai", retryable=True)
    assert exc.provider == "openai"
    assert exc.retryable is True

    auth = AuthorizationError("denied", tool_name="echo")
    assert auth.tool_name == "echo"
