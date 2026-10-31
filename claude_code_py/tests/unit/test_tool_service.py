from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.tools import ToolExecutionRequest
from claude_code_py.tools import build_default_tool_registry
from tests.helpers import make_tool_context


def test_tool_service_wraps_messages(tmp_path) -> None:
    service = ToolService(build_default_tool_registry())
    context = make_tool_context(tmp_path)

    envelope = service.execute(
        ToolExecutionRequest(
            tool_name="Write",
            arguments={"file_path": "notes.txt", "content": "hello"},
        ),
        context,
    )

    assert envelope.use_message.kind == "tool_use"
    assert envelope.result_message.kind == "tool_result"
    assert envelope.use_message.tool_use_id == envelope.result_message.tool_use_id
    assert envelope.result.tool_name == "Write"
    assert envelope.result.is_error is False
    assert envelope.summary == "notes.txt"


def test_tool_service_captures_tool_errors(tmp_path) -> None:
    service = ToolService(build_default_tool_registry())
    context = make_tool_context(tmp_path)

    envelope = service.execute(
        ToolExecutionRequest(
            tool_name="Edit",
            arguments={
                "file_path": "missing.txt",
                "old_string": "a",
                "new_string": "b",
            },
        ),
        context,
    )

    assert envelope.result.is_error is True
    assert envelope.result_message.is_error is True


def test_tool_service_uses_validation_summary_for_bash(tmp_path) -> None:
    service = ToolService(build_default_tool_registry())
    context = make_tool_context(tmp_path)

    envelope = service.execute(
        ToolExecutionRequest(
            tool_name="Bash",
            arguments={"command": "   "},
        ),
        context,
    )

    assert envelope.summary == "Bash invocation"
    assert envelope.result.is_error is True
