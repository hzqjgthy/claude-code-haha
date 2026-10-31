from typing import Any

from pydantic import BaseModel, Field

from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.messages import AssistantMessage, Message, UserMessage
from claude_code_py.domain.tools import ToolExecutionRequest
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.tools.base import ToolContext


class QueryRequest(BaseModel):
    prompt: str
    model: str
    history: list[Message] = Field(default_factory=list)
    system_prompt: str | None = None
    max_tokens: int = 4096


class QueryResult(BaseModel):
    model: str
    text: str
    new_messages: list[Message] = Field(default_factory=list)
    messages: list[Message] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class QueryService:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        tool_service: ToolService | None = None,
        tool_context: ToolContext | None = None,
        max_tool_rounds: int = 100,
    ) -> None:
        self._provider = provider
        self._tool_service = tool_service
        self._tool_context = tool_context
        self._max_tool_rounds = max_tool_rounds

    def submit(self, request: QueryRequest) -> QueryResult:
        user_message = UserMessage(content=request.prompt)
        messages = [*request.history, user_message]
        new_messages: list[Message] = [user_message]
        latest_text = ""
        last_completion: CompletionResponse | None = None

        for _ in range(self._max_tool_rounds):
            completion = self._provider.complete(
                CompletionRequest(
                    model=request.model,
                    messages=messages,
                    tools=self._tool_service.list_specs() if self._tool_service else [],
                    system_prompt=request.system_prompt,
                    max_tokens=request.max_tokens,
                ),
            )
            last_completion = completion

            if completion.text:
                assistant_message = AssistantMessage(content=completion.text)
                messages.append(assistant_message)
                new_messages.append(assistant_message)
                latest_text = completion.text

            if not completion.tool_calls:
                break

            if self._tool_service is None or self._tool_context is None:
                break

            self._tool_context.metadata["current_turn_id"] = user_message.id
            self._tool_context.metadata["conversation_history"] = list(messages)
            self._tool_context.metadata["system_prompt"] = request.system_prompt
            self._tool_context.metadata["current_model"] = request.model
            for tool_call in completion.tool_calls:
                envelope = self._tool_service.execute(
                    ToolExecutionRequest(
                        tool_name=tool_call.tool_name,
                        tool_use_id=tool_call.tool_use_id,
                        arguments=tool_call.arguments,
                    ),
                    self._tool_context,
                )
                messages.extend([envelope.use_message, envelope.result_message])
                new_messages.extend([envelope.use_message, envelope.result_message])

        if last_completion is None:
            raise RuntimeError("Query loop finished without any provider completion.")

        return QueryResult(
            model=last_completion.model,
            text=latest_text,
            new_messages=new_messages,
            messages=messages,
            raw_response=last_completion.raw_response,
        )
