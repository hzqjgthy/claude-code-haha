from claude_code_py.application.permission_service import PermissionService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.tools import ToolExecutionRequest
from tests.helpers import make_test_container, make_tool_context
from claude_code_py.tools import build_default_tool_registry


def test_tool_service_respects_deny_rule(tmp_path) -> None:
    container = make_test_container(tmp_path)
    permission_service = PermissionService.from_sources(
        container=container,
        workspace_root=make_tool_context(tmp_path).workspace_root,
        mode="default",
        ask_mode_enabled=False,
        deny_rules=["Write"],
    )
    service = ToolService(
        build_default_tool_registry(),
        permission_service=permission_service,
    )
    context = make_tool_context(tmp_path)

    envelope = service.execute(
        ToolExecutionRequest(
            tool_name="Write",
            arguments={"file_path": "blocked.txt", "content": "hello"},
        ),
        context,
    )

    assert envelope.result.is_error is True
    assert "Matched cli_arg rule" in envelope.result.output


def test_permission_mode_accept_edits_blocks_bash_without_ui(tmp_path) -> None:
    container = make_test_container(tmp_path)
    permission_service = PermissionService.from_sources(
        container=container,
        workspace_root=make_tool_context(tmp_path).workspace_root,
        mode="accept_edits",
        ask_mode_enabled=False,
    )
    service = ToolService(
        build_default_tool_registry(),
        permission_service=permission_service,
    )
    context = make_tool_context(tmp_path)

    bash = service.execute(
        ToolExecutionRequest(tool_name="Bash", arguments={"command": "echo hi"}),
        context,
    )
    write = service.execute(
        ToolExecutionRequest(
            tool_name="Write",
            arguments={"file_path": "ok.txt", "content": "hello"},
        ),
        context,
    )

    assert bash.result.is_error is True
    assert write.result.is_error is False


def test_tool_service_can_persist_project_approval_from_callback(tmp_path) -> None:
    container = make_test_container(tmp_path)
    permission_service = PermissionService.from_sources(
        container=container,
        workspace_root=make_tool_context(tmp_path).workspace_root,
        mode="default",
        ask_mode_enabled=True,
        ask_rules=["Write(path:*)"],
    )
    service = ToolService(
        build_default_tool_registry(),
        permission_service=permission_service,
    )
    context = make_tool_context(tmp_path)
    context.metadata["permission_prompt_callback"] = lambda request: "allow_project"

    envelope = service.execute(
        ToolExecutionRequest(
            tool_name="Write",
            arguments={"file_path": "persisted.txt", "content": "hello"},
        ),
        context,
    )

    settings_path = context.workspace_root / ".claude_code_py" / "settings.json"
    assert envelope.result.is_error is False
    assert settings_path.exists() is True
    assert "Write(path:" in settings_path.read_text(encoding="utf-8")
