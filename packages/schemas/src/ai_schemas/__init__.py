"""Shared Pydantic models and JSON-compatible contracts.

Rules:
- no provider SDK dependencies;
- no database dependencies;
- no network access.
"""

from ai_schemas.messages import Message, Role
from ai_schemas.usage import Usage

__all__ = ["Message", "Role", "Usage"]
