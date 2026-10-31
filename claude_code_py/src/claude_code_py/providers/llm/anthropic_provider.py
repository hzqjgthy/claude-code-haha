from typing import Any

import httpx

from claude_code_py.app.settings import AppSettings
from claude_code_py.domain.messages import (
    AssistantMessage,
    Message,
    ToolResultMessage,
    ToolUseMessage,
    UserMessage,
)
from claude_code_py.domain.tools import ToolCall, ToolSpec
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMConfigurationError,
    LLMProvider,
    LLMProviderError,
)

ANTHROPIC_VERSION = "2023-06-01"


def _messages_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/messages"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/messages"
    return f"{normalized}/v1/messages"


class AnthropicLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str | None,
        auth_token: str | None,
        base_url: str,
        timeout_ms: int,
    ) -> None:
        if not api_key and not auth_token:
            raise LLMConfigurationError(
                "Missing credentials: set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN.",
            )
        self._api_key = api_key
        self._auth_token = auth_token
        self._messages_url = _messages_url(base_url)
        self._timeout = max(timeout_ms / 1000.0, 1.0)

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "AnthropicLLMProvider":
        return cls(
            api_key=settings.anthropic_api_key,
            auth_token=settings.anthropic_auth_token,
            base_url=settings.anthropic_base_url,
            timeout_ms=settings.api_timeout_ms,
        )

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        headers = {
            "content-type": "application/json",
            "accept": "application/json",
            "anthropic-version": ANTHROPIC_VERSION,
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        elif self._auth_token:
            headers["authorization"] = f"Bearer {self._auth_token}"

        payload: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": self._serialize_messages(request.messages),
        }
        if request.tools:
            payload["tools"] = self._serialize_tools(request.tools)
        if request.system_prompt:
            payload["system"] = request.system_prompt

        try:
            response = httpx.post(
                self._messages_url,
                headers=headers,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Anthropic request failed: {exc}") from exc

        raw_response = response.json()
        content = raw_response.get("content", [])
        text_blocks = [
            block.get("text", "")
            for block in content
            if block.get("type") == "text"
        ]
        tool_calls = [
            ToolCall(
                tool_use_id=str(block["id"]),
                tool_name=str(block["name"]),
                arguments=dict(block.get("input", {})),
            )
            for block in content
            if block.get("type") == "tool_use"
        ]
        text = "\n".join(block for block in text_blocks if block).strip()
        if not text and not tool_calls:
            raise LLMProviderError("Anthropic response did not include text content.")

        model = str(raw_response.get("model", request.model))
        return CompletionResponse(
            model=model,
            text=text,
            stop_reason=str(raw_response.get("stop_reason", "end_turn")),
            tool_calls=tool_calls,
            raw_response=raw_response,
        )

    @staticmethod
    def _serialize_messages(messages: list[Message]) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for message in messages:
            role, content_block = AnthropicLLMProvider._serialize_message(message)
            if serialized and serialized[-1]["role"] == role:
                existing = serialized[-1]["content"]
                if isinstance(existing, list):
                    existing.append(content_block)
                else:
                    serialized[-1]["content"] = [existing, content_block]
            else:
                serialized.append({"role": role, "content": [content_block]})
        return serialized

    @staticmethod
    def _serialize_message(message: Message) -> tuple[str, dict[str, Any]]:
        if isinstance(message, UserMessage):
            return ("user", {"type": "text", "text": message.content})
        if isinstance(message, AssistantMessage):
            return ("assistant", {"type": "text", "text": message.content})
        if isinstance(message, ToolUseMessage):
            return (
                "assistant",
                {
                    "type": "tool_use",
                    "id": message.tool_use_id,
                    "name": message.tool_name,
                    "input": message.arguments,
                },
            )
        if isinstance(message, ToolResultMessage):
            return (
                "user",
                {
                    "type": "tool_result",
                    "tool_use_id": message.tool_use_id,
                    "content": message.output,
                    "is_error": message.is_error,
                },
            )
        raise TypeError(f"Unsupported message type: {type(message)!r}")

    @staticmethod
    def _serialize_tools(tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in tools
        ]
