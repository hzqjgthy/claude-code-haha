import json

from tests.helpers import make_test_container, make_tool_context

from claude_code_py.application.permission_service import PermissionService
from claude_code_py.domain.permissions import PermissionTarget
from claude_code_py.permissions.engine import PermissionEngine
from claude_code_py.permissions.rules import build_context, parse_permission_rule
from claude_code_py.tools import build_default_tool_registry


def test_parse_permission_rule_supports_matchers() -> None:
    rule = parse_permission_rule(
        "Write(path:docs/*.md)",
        source="cli_arg",
        behavior="allow",
    )

    assert rule.tool_name == "Write"
    assert rule.kind == "path"
    assert rule.pattern == "docs/*.md"


def test_permission_engine_prefers_deny_over_allow() -> None:
    allow_rule = parse_permission_rule(
        "Write", source="user_settings", behavior="allow"
    )
    deny_rule = parse_permission_rule("Write", source="cli_arg", behavior="deny")
    context = build_context(
        mode="default",
        ask_mode_enabled=False,
        rules=[allow_rule, deny_rule],
    )
    decision = PermissionEngine().evaluate(
        context,
        [PermissionTarget(tool_name="Write")],
    )

    assert decision.behavior == "deny"
    assert decision.source == "cli_arg"


def test_permission_engine_turns_ask_into_deny_when_no_ui() -> None:
    ask_rule = parse_permission_rule(
        "WebFetch(domain:github.com)",
        source="cli_arg",
        behavior="ask",
    )
    context = build_context(
        mode="default",
        ask_mode_enabled=False,
        rules=[ask_rule],
    )
    decision = PermissionEngine().evaluate(
        context,
        [PermissionTarget(tool_name="WebFetch", kind="domain", value="github.com")],
    )

    assert decision.behavior == "deny"
    assert "approval" in (decision.reason or "")


def test_permission_service_loads_user_and_project_rules(tmp_path) -> None:
    container = make_test_container(tmp_path)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    user_settings_dir = container.paths.data_dir / "settings"
    user_settings_dir.mkdir(parents=True, exist_ok=True)
    (user_settings_dir / "user_settings.json").write_text(
        json.dumps({"allow": ["Read"]}),
        encoding="utf-8",
    )
    project_settings_dir = workspace_root / ".claude_code_py"
    project_settings_dir.mkdir(parents=True, exist_ok=True)
    (project_settings_dir / "settings.json").write_text(
        json.dumps({"deny": ["Write"]}),
        encoding="utf-8",
    )

    service = PermissionService.from_sources(
        container=container,
        workspace_root=workspace_root,
        mode="default",
        ask_mode_enabled=False,
    )

    read_tool = build_default_tool_registry().get("Read")
    write_tool = build_default_tool_registry().get("Write")
    context = make_tool_context(tmp_path)

    read_payload = read_tool.input_model.model_validate({"file_path": "a.txt"})
    write_payload = write_tool.input_model.model_validate(
        {"file_path": "a.txt", "content": "x"},
    )

    read_decision = service.evaluate(read_tool, read_payload, context)
    write_decision = service.evaluate(write_tool, write_payload, context)

    assert read_decision.behavior == "allow"
    assert write_decision.behavior == "deny"


def test_permission_service_accepts_original_mode_alias(tmp_path) -> None:
    container = make_test_container(tmp_path)
    context = make_tool_context(tmp_path)
    service = PermissionService.from_sources(
        container=container,
        workspace_root=context.workspace_root,
        mode="acceptEdits",
        ask_mode_enabled=False,
    )
    bash_tool = build_default_tool_registry().get("Bash")
    bash_payload = bash_tool.input_model.model_validate({"command": "echo hi"})

    decision = service.evaluate(bash_tool, bash_payload, context)

    assert decision.behavior == "deny"
    assert "accept_edits mode" in (decision.reason or "")


def test_session_rules_override_ask_rules_for_interactive_memory() -> None:
    ask_rule = parse_permission_rule(
        "Write(path:/tmp/demo.txt)",
        source="cli_arg",
        behavior="ask",
    )
    allow_rule = parse_permission_rule(
        "Write(path:/tmp/demo.txt)",
        source="session",
        behavior="allow",
    )
    context = build_context(
        mode="default",
        ask_mode_enabled=True,
        rules=[ask_rule, allow_rule],
    )

    decision = PermissionEngine().evaluate(
        context,
        [PermissionTarget(tool_name="Write", kind="path", value="/tmp/demo.txt")],
    )

    assert decision.behavior == "allow"
    assert decision.source == "session"


def test_permission_service_can_persist_project_rules_and_track_denials(
    tmp_path,
) -> None:
    container = make_test_container(tmp_path)
    context = make_tool_context(tmp_path)
    service = PermissionService.from_sources(
        container=container,
        workspace_root=context.workspace_root,
        mode="default",
        ask_mode_enabled=True,
    )

    remembered = service.remember_targets(
        [PermissionTarget(tool_name="Write", kind="path", value="/tmp/demo.txt")],
        behavior="allow",
        destination="project_settings",
    )
    service.record_denial(
        tool_name="WebFetch",
        summary="https://example.com",
        reason="Denied in test",
        request_kind="web_fetch",
        targets=[PermissionTarget(tool_name="WebFetch", kind="domain", value="example.com")],
    )

    settings_path = context.workspace_root / ".claude_code_py" / "settings.json"
    raw = json.loads(settings_path.read_text(encoding="utf-8"))

    assert remembered[0].source == "project_settings"
    assert "Write(path:/tmp/demo.txt)" in raw["allow"]
    denials = service.list_recent_denials()
    assert denials[0].tool_name == "WebFetch"
    assert denials[0].request_kind == "web_fetch"


def test_permission_service_detects_shadowed_rules(tmp_path) -> None:
    container = make_test_container(tmp_path)
    context = make_tool_context(tmp_path)
    service = PermissionService.from_sources(
        container=container,
        workspace_root=context.workspace_root,
        mode="default",
        ask_mode_enabled=True,
        allow_rules=["Write(path:/tmp/demo.txt)"],
        deny_rules=["Write"],
    )

    shadowed = service.detect_shadowed_rules()

    assert len(shadowed) == 1
    assert shadowed[0].shadow_type == "deny"
    assert shadowed[0].rule.tool_name == "Write"
