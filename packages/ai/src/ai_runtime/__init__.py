"""Provider-independent AI abstractions."""

from ai_runtime.fake import FakeChatModel
from ai_runtime.models import ChatModel, GenerationRequest, GenerationResult, ToolCall
from ai_runtime.structured import parse_structured_output

__all__ = [
    "ChatModel",
    "FakeChatModel",
    "GenerationRequest",
    "GenerationResult",
    "ToolCall",
    "parse_structured_output",
]
