from pathlib import Path

from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.tools import ToolExecutionRequest
from claude_code_py.tools import build_default_tool_registry
from claude_code_py.tools.file_context import list_file_context_paths
from tests.helpers import make_tool_context


def test_write_read_and_edit_tools_roundtrip(tmp_path) -> None:
    service = ToolService(build_default_tool_registry())
    context = make_tool_context(tmp_path)

    write_result = service.execute(
        ToolExecutionRequest(
            tool_name="Write",
            arguments={"file_path": "docs/example.txt", "content": "alpha\nbeta\n"},
        ),
        context,
    )
    assert write_result.result.is_error is False

    read_result = service.execute(
        ToolExecutionRequest(
            tool_name="Read",
            arguments={"file_path": "docs/example.txt"},
        ),
        context,
    )
    assert "alpha" in read_result.result.output
    assert "beta" in read_result.result.output

    edit_result = service.execute(
        ToolExecutionRequest(
            tool_name="Edit",
            arguments={
                "file_path": "docs/example.txt",
                "old_string": "beta",
                "new_string": "gamma",
            },
        ),
        context,
    )
    assert edit_result.result.is_error is False

    final_text = (context.workspace_root / "docs" / "example.txt").read_text(encoding="utf-8")
    assert final_text == "alpha\ngamma\n"
    tracked = list_file_context_paths(context)
    assert tracked[-1] == context.workspace_root / "docs" / "example.txt"


def test_edit_tool_rejects_noop_replacement(tmp_path) -> None:
    service = ToolService(build_default_tool_registry())
    context = make_tool_context(tmp_path)
    target = context.workspace_root / "same.txt"
    target.write_text("hello", encoding="utf-8")

    result = service.execute(
        ToolExecutionRequest(
            tool_name="Edit",
            arguments={
                "file_path": "same.txt",
                "old_string": "hello",
                "new_string": "hello",
            },
        ),
        context,
    )

    assert result.result.is_error is True
