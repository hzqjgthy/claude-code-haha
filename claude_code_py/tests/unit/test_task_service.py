from claude_code_py.application.query_service import QueryRequest
from claude_code_py.application.task_service import TaskService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.messages import ToolResultMessage
from claude_code_py.providers.llm.base import CompletionRequest, CompletionResponse, LLMProvider
from claude_code_py.tools import build_default_tool_registry
from tests.helpers import make_tool_context


class FakeProvider(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        prompt = request.messages[-1].content  # type: ignore[union-attr]
        return CompletionResponse(
            model=request.model,
            text=f"assistant:{prompt}",
            raw_response={"model": request.model},
        )


def test_task_service_runs_sync_subagent(tmp_path) -> None:
    provider = FakeProvider()
    tool_context = make_tool_context(tmp_path, llm_provider=provider)
    task_service = TaskService(allow_background=True)
    task_service.configure(
        provider=provider,
        tool_service=ToolService(build_default_tool_registry()),
        tool_context=tool_context,
        default_max_tokens=256,
    )

    submission = task_service.submit_agent_task(
        description="subtask",
        prompt="hello",
        history=[],
        model="test-model",
        system_prompt=None,
        session_id="sess-1",
        background=False,
    )

    assert submission.result is not None
    assert submission.result.text == "assistant:hello"
    task = task_service.get_task(submission.task.task_id)
    assert task is not None
    assert task.status == "completed"
    assert task.result_text == "assistant:hello"


def test_task_service_supports_task_kind_owner_and_metadata(tmp_path) -> None:
    provider = FakeProvider()
    tool_context = make_tool_context(tmp_path, llm_provider=provider)
    task_service = TaskService(allow_background=True)
    task_service.configure(
        provider=provider,
        tool_service=ToolService(build_default_tool_registry()),
        tool_context=tool_context,
        default_max_tokens=256,
    )

    submission = task_service.submit_agent_task(
        description="workflow-subtask",
        prompt="hello workflow",
        history=[],
        model="test-model",
        system_prompt=None,
        session_id="sess-1",
        background=False,
        kind="workflow",
        owner="planner",
        metadata={"workflow_name": "release"},
    )

    task = task_service.get_task(submission.task.task_id)
    assert task is not None
    assert task.kind == "workflow"
    assert task.owner == "planner"
    assert task.metadata["workflow_name"] == "release"


def test_task_service_runs_background_task_and_emits_event(tmp_path) -> None:
    provider = FakeProvider()
    tool_context = make_tool_context(tmp_path, llm_provider=provider)
    task_service = TaskService(allow_background=True)
    task_service.configure(
        provider=provider,
        tool_service=ToolService(build_default_tool_registry()),
        tool_context=tool_context,
        default_max_tokens=256,
    )

    submission = task_service.submit_agent_task(
        description="background-subtask",
        prompt="hello background",
        history=[],
        model="test-model",
        system_prompt=None,
        session_id="sess-1",
        background=True,
    )
    task = task_service.wait_for_task(submission.task.task_id, timeout=2)
    events = task_service.drain_events()

    assert task.status == "completed"
    assert task.result_text == "assistant:hello background"
    assert len(events) == 1
    assert "completed" in events[0].message
