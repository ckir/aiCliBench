"""Minimal JSON-schema-subset validation for tool arguments.

Supports the object-shape subset produced by Pydantic ``model_json_schema()``
and hand-written specs: ``type: object`` with ``properties``, ``required``,
``additionalProperties``, per-property ``type``/``enum``, and nested objects.
"""

from __future__ import annotations

from typing import Any

from ai_core.errors import ValidationError

_SCALAR_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
    "null": (type(None),),
}


def _check_type(value: Any, expected: str, *, field_path: str) -> None:
    if expected not in _SCALAR_TYPES:
        return  # Unknown/union types are accepted; plugins validate deeply.
    # Note: ``bool`` is a subclass of ``int``; exclude it from integer/number.
    if expected in ("integer", "number") and isinstance(value, bool):
        raise ValidationError(f"field {field_path!r} must be {expected}", field=field_path)
    if not isinstance(value, _SCALAR_TYPES[expected]):
        raise ValidationError(f"field {field_path!r} must be {expected}", field=field_path)


def _validate_value(value: Any, schema: dict[str, Any], *, field_path: str) -> None:
    if "enum" in schema and value not in schema["enum"]:
        raise ValidationError(f"field {field_path!r} is not an allowed value", field=field_path)
    expected = schema.get("type")
    if isinstance(expected, str):
        _check_type(value, expected, field_path=field_path)
    if isinstance(value, dict) and isinstance(schema.get("properties"), dict):
        _validate_object(value, schema, field_path=field_path)


def _validate_object(args: dict[str, Any], schema: dict[str, Any], *, field_path: str = "") -> None:
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, dict):
        raise ValidationError("invalid schema: properties must be an object")
    if not isinstance(required, list):
        raise ValidationError("invalid schema: required must be a list")
    for name in required:
        if name not in args:
            path = f"{field_path}.{name}" if field_path else name
            raise ValidationError(f"missing required field {path!r}", field=path)
    additional = schema.get("additionalProperties", True)
    for key, value in args.items():
        path = f"{field_path}.{key}" if field_path else key
        prop_schema = properties.get(key)
        if prop_schema is None:
            if additional is False:
                raise ValidationError(f"unexpected field {path!r}", field=path)
            continue
        if isinstance(prop_schema, dict):
            _validate_value(value, prop_schema, field_path=path)


def validate_args(args: Any, schema: dict[str, Any]) -> None:
    """Validate JSON-compatible ``args`` against an object ``schema``.

    Raises:
        ValidationError: on any shape/type mismatch.
    """
    if not isinstance(schema, dict) or not schema:
        raise ValidationError("tool input schema is missing or invalid")
    if schema.get("type", "object") != "object":
        raise ValidationError("tool input schema must describe an object")
    if not isinstance(args, dict):
        raise ValidationError("tool arguments must be an object")
    _validate_object(args, schema)
