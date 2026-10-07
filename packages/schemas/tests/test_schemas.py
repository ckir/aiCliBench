import pytest
from pydantic import ValidationError as PydanticValidationError

from ai_schemas import Message, Usage


def test_schemas_package_imports():
    import ai_schemas

    assert ai_schemas is not None


def test_message_validation():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"

    with pytest.raises(PydanticValidationError):
        Message(role="user", content="")

    with pytest.raises(PydanticValidationError):
        Message.model_validate({"role": "nobody", "content": "hi"})


def test_usage_normalization():
    usage = Usage(input_tokens=3, output_tokens=4).normalized()
    assert usage.total_tokens == 7

    explicit = Usage(input_tokens=3, output_tokens=4, total_tokens=10).normalized()
    assert explicit.total_tokens == 10


def test_schemas_have_no_provider_deps():
    # Schemas must not import provider SDKs or perform network I/O at import time.
    import sys

    for module in ("openai", "anthropic", "google", "httpx"):
        assert f"ai_schemas.{module}" not in sys.modules
