from claude_code_py.application.task_service import TaskService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.tools import ToolExecutionRequest
from claude_code_py.providers.llm.base import CompletionRequest, CompletionResponse, LLMProvider
from claude_code_py.tools import build_default_tool_registry
from claude_code_py.tools.agent import AgentTool
from tests.helpers import make_tool_context


class FakeProvider(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        prompt = request.messages[-1].content  # type: ignore[union-attr]
        return CompletionResponse(
            model=request.model,
            text=f"child:{prompt}",
            raw_response={"ok": True},
        )


def test_agent_tool_runs_sync_subagent(tmp_path) -> None:
    provider = FakeProvider()
    context = make_tool_context(tmp_path, llm_provider=provider)
    task_service = TaskService(allow_background=True)
    tool_service = ToolService(
        build_default_tool_registry(extra_tools=[AgentTool()]),
    )
    task_service.configure(
        provider=provider,
        tool_service=tool_service,
        tool_context=context,
        default_max_tokens=256,
    )
    context.metadata["task_service"] = task_service
    context.metadata["conversation_history"] = []
    context.metadata["current_model"] = "test-model"
    context.metadata["session_id"] = "sess-1"

    envelope = tool_service.execute(
        ToolExecutionRequest(
            tool_name="Agent",
            arguments={
                "description": "subtask",
                "prompt": "hello",
            },
        ),
        context,
    )

    assert envelope.result.is_error is False
    assert envelope.result.output == "child:hello"
    assert provider.requests[0].model == "test-model"


def test_agent_tool_launches_background_task(tmp_path) -> None:
    provider = FakeProvider()
    context = make_tool_context(tmp_path, llm_provider=provider)
    task_service = TaskService(allow_background=True)
    tool_service = ToolService(
        build_default_tool_registry(extra_tools=[AgentTool()]),
    )
    task_service.configure(
        provider=provider,
        tool_service=tool_service,
        tool_context=context,
        default_max_tokens=256,
    )
    context.metadata["task_service"] = task_service
    context.metadata["conversation_history"] = []
    context.metadata["current_model"] = "test-model"
    context.metadata["session_id"] = "sess-1"

    envelope = tool_service.execute(
        ToolExecutionRequest(
            tool_name="Agent",
            arguments={
                "description": "bg-subtask",
                "prompt": "hello bg",
                "run_in_background": True,
            },
        ),
        context,
    )
    task_id = envelope.result.structured_output["task_id"]
    task = task_service.wait_for_task(task_id, timeout=2)

    assert envelope.result.is_error is False
    assert "Background task started." in envelope.result.output
    assert task.status == "completed"
