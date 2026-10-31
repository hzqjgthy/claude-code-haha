from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.tools import ToolExecutionRequest
from claude_code_py.tools import build_default_tool_registry
from tests.helpers import make_tool_context


def test_bash_tool_executes_command(tmp_path) -> None:
    service = ToolService(build_default_tool_registry())
    context = make_tool_context(tmp_path)

    envelope = service.execute(
        ToolExecutionRequest(
            tool_name="Bash",
            arguments={"command": "printf 'hello from bash'"},
        ),
        context,
    )

    assert envelope.result.is_error is False
    assert "hello from bash" in envelope.result.output
