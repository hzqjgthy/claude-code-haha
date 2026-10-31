from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from claude_code_py.domain.messages import Message
from claude_code_py.domain.tools import ToolCall, ToolSpec


class CompletionRequest(BaseModel):
    model: str
    messages: list[Message] = Field(default_factory=list)
    tools: list[ToolSpec] = Field(default_factory=list)
    system_prompt: str | None = None
    max_tokens: int = 4096


class CompletionResponse(BaseModel):
    model: str
    text: str = ""
    stop_reason: str = "end_turn"
    tool_calls: list[ToolCall] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class LLMProviderError(RuntimeError):
    """Raised when the configured LLM provider cannot complete a request."""


class LLMConfigurationError(LLMProviderError):
    """Raised when the configured LLM provider is missing required settings."""


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        raise NotImplementedError
