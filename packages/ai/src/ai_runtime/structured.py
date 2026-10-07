"""Structured-output validation. Model output is untrusted input."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ai_core.errors import ValidationError


def parse_structured_output[T: BaseModel](model: type[T], payload: object) -> T:
    """Validate an untrusted model payload against a Pydantic model.

    Raises:
        ValidationError: when the payload does not conform to ``model``.
    """
    try:
        if isinstance(payload, str):
            return model.model_validate_json(payload)
        if isinstance(payload, dict):
            return model.model_validate(payload)
        raise ValidationError(f"unsupported structured payload type: {type(payload).__name__}")
    except PydanticValidationError as exc:
        raise ValidationError(f"invalid structured output for {model.__name__}: {exc}") from exc
