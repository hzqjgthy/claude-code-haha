from claude_code_py.application.query_service import QueryRequest, QueryService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.messages import AssistantMessage
from claude_code_py.domain.tools import ToolCall
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.tools import build_default_tool_registry
from tests.helpers import make_tool_context


class FakeProvider(LLMProvider):
    def __init__(self) -> None:
        self.last_request: CompletionRequest | None = None

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.last_request = request
        prompt = request.messages[-1].content  # type: ignore[union-attr]
        return CompletionResponse(
            model=request.model,
            text=f"echo:{prompt}",
            raw_response={"ok": True},
        )


def test_query_service_builds_user_and_assistant_messages() -> None:
    provider = FakeProvider()
    service = QueryService(provider)

    result = service.submit(
        QueryRequest(
            prompt="hello",
            model="test-model",
            system_prompt="system",
            max_tokens=128,
        ),
    )

    assert provider.last_request is not None
    assert provider.last_request.system_prompt == "system"
    assert result.text == "echo:hello"
    assert len(result.new_messages) == 2
    assert len(result.messages) == 2
    assert result.messages[0].kind == "user"
    assert result.messages[1].kind == "assistant"


def test_query_service_preserves_history() -> None:
    provider = FakeProvider()
    service = QueryService(provider)

    result = service.submit(
        QueryRequest(
            prompt="follow-up",
            model="test-model",
            history=[AssistantMessage(content="previous answer")],
        ),
    )

    assert provider.last_request is not None
    assert len(provider.last_request.messages) == 2
    assert result.messages[0].kind == "assistant"
    assert result.messages[-1].kind == "assistant"


class ToolLoopProvider(LLMProvider):
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.calls += 1
        if self.calls == 1:
            assert any(tool.name == "Write" for tool in request.tools)
            return CompletionResponse(
                model=request.model,
                stop_reason="tool_use",
                tool_calls=[
                    ToolCall(
                        tool_use_id="toolu_1",
                        tool_name="Write",
                        arguments={"file_path": "note.txt", "content": "hello"},
                    )
                ],
                raw_response={"phase": 1},
            )
        assert any(message.kind == "tool_result" for message in request.messages)
        return CompletionResponse(
            model=request.model,
            text="finished after tool",
            raw_response={"phase": 2},
        )


def test_query_service_executes_tool_loop(tmp_path) -> None:
    provider = ToolLoopProvider()
    service = QueryService(
        provider,
        tool_service=ToolService(build_default_tool_registry()),
        tool_context=make_tool_context(tmp_path),
    )

    result = service.submit(
        QueryRequest(
            prompt="write a file",
            model="test-model",
        ),
    )

    assert provider.calls == 2
    assert result.text == "finished after tool"
    assert [message.kind for message in result.new_messages] == [
        "user",
        "tool_use",
        "tool_result",
        "assistant",
    ]
