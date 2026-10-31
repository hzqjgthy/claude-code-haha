import json
import os
from pathlib import Path
import subprocess
import sys
from time import sleep, time

from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.domain.tools import ToolCall
from claude_code_py.tools.file_read import FileReadTool, FileReadToolInput
from claude_code_py.ui.textual.controller import TextualSessionController
from claude_code_py.cli.repl_mode import ReplModeParams
from tests.helpers import make_test_container


class FakeProvider(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        prompt = request.messages[-1].content  # type: ignore[union-attr]
        return CompletionResponse(
            model=request.model,
            text=f"assistant:{prompt}",
            raw_response={
                "model": request.model,
                "usage": {
                    "input_tokens": 11,
                    "output_tokens": 7,
                    "cache_read_input_tokens": 3,
                    "cache_creation_input_tokens": 2,
                },
            },
        )


class FileWriteProvider(LLMProvider):
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        last_message = request.messages[-1]
        if last_message.kind == "tool_result":
            return CompletionResponse(
                model=request.model,
                text="assistant:done",
                raw_response={"phase": "assistant"},
            )
        prompt = last_message.content  # type: ignore[union-attr]
        if "write alpha" in prompt:
            content = "alpha"
        elif "write beta" in prompt:
            content = "beta"
        else:
            content = "default"
        return CompletionResponse(
            model=request.model,
            stop_reason="tool_use",
            tool_calls=[
                ToolCall(
                    tool_use_id="toolu_write",
                    tool_name="Write",
                    arguments={"file_path": "notes.txt", "content": content},
                )
            ],
            raw_response={"phase": "tool"},
        )


class RemotePermissionProvider(LLMProvider):
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        last_message = request.messages[-1]
        if last_message.kind == "tool_result":
            return CompletionResponse(
                model=request.model,
                text="remote-finished",
                raw_response={"phase": "assistant"},
            )
        prompt = last_message.content  # type: ignore[union-attr]
        if "remote write" in prompt:
            return CompletionResponse(
                model=request.model,
                stop_reason="tool_use",
                tool_calls=[
                    ToolCall(
                        tool_use_id="toolu_remote_1",
                        tool_name="Write",
                        arguments={"file_path": "remote.txt", "content": "hello remote"},
                    )
                ],
                raw_response={"phase": "tool"},
            )
        return CompletionResponse(
            model=request.model,
            text=f"remote:{prompt}",
            raw_response={"phase": "assistant"},
        )


def test_permissions_command_can_update_mode_and_rules(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1", permission_mode="bypass_permissions"),
        provider=provider,
    )

    try:
        mode_result = controller.submit_prompt("/permissions mode bypass_permissions")
        assert mode_result[0].text == "Permission mode updated to bypass_permissions."
        assert controller.status_snapshot().permission_mode == "bypass_permissions"

        allow_result = controller.submit_prompt("/permissions allow Read(path:src/*)")
        assert allow_result[0].text == "Added session allow rule: Read(path:src/*)"

        summary = controller.submit_prompt("/permissions")
        assert "mode: bypass_permissions" in summary[0].text
        assert "allow | source=session | Read(path:src/*)" in summary[0].text
        assert "shadowed_rule_count:" in summary[0].text
    finally:
        controller.shutdown()


def test_rename_command_updates_current_session_title(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        rename_result = controller.submit_prompt("/rename Learning session")
        assert "Renamed session sess-1 to 'Learning session'." == rename_result[0].text
        assert controller.status_detail_snapshot().session_title == "Learning session"

        current = controller.submit_prompt("/rename")
        assert current[0].text == "Current session title: Learning session"
    finally:
        controller.shutdown()


def test_files_command_lists_tracked_tool_context_files(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        target = workspace_root / "docs" / "example.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("hello", encoding="utf-8")
        FileReadTool().execute(
            FileReadToolInput(file_path="docs/example.txt"),
            controller._tool_context,
        )
        files_result = controller.submit_prompt("/files")
        assert "Files in context: 1" in files_result[0].text
        assert "docs/example.txt" in files_result[0].text

        cleared = controller.submit_prompt("/files clear")
        assert cleared[0].text == "Cleared 1 tracked file(s) from context."
    finally:
        controller.shutdown()


def test_plugin_command_lists_and_shows_loaded_plugins(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    plugin_root = tmp_path / "demo-plugin"
    command_dir = plugin_root / "commands"
    skill_dir = plugin_root / "skills"
    monkeypatch.chdir(workspace_root)

    command_dir.mkdir(parents=True, exist_ok=True)
    skill_dir.mkdir(parents=True, exist_ok=True)
    (plugin_root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin_root / ".claude-plugin" / "plugin.json").write_text(
        (
            '{'
            '"name":"demo-plugin",'
            '"version":"1.0.0",'
            '"description":"Demo plugin",'
            '"commands":["./commands"],'
            '"skills":["./skills"]'
            '}'
        ),
        encoding="utf-8",
    )

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1", plugin_dirs=[str(plugin_root)]),
        provider=provider,
    )

    try:
        overview = controller.submit_prompt("/plugin")
        assert "demo-plugin | scope=cli_arg" in overview[0].text
        selector = controller.consume_requested_selector_dialog()
        assert selector is not None
        assert selector.kind == "selector:plugin"
        assert any(
            option.command == "/plugin show demo-plugin"
            for option in selector.options
        )

        details = controller.submit_prompt("/plugin show demo-plugin")
        assert "name: demo-plugin" in details[0].text
        assert "version: 1.0.0" in details[0].text
    finally:
        controller.shutdown()


def test_plugin_marketplace_install_validate_and_trust_phase20(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    source_plugin = tmp_path / "market-plugin-source"
    source_plugin.mkdir(parents=True, exist_ok=True)
    (source_plugin / "plugin.json").write_text(
        '{"name":"market-plugin","description":"Plugin from marketplace"}',
        encoding="utf-8",
    )
    catalog_dir = workspace_root / ".claude" / "marketplaces"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / "demo.json").write_text(
        (
            '{'
            '"name":"demo-market",'
            '"plugins":[{"name":"market-plugin","path":"'
            + str(source_plugin).replace("\\", "\\\\")
            + '","description":"Plugin from marketplace","requires_trust":true}]'
            '}'
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        marketplace = controller.submit_prompt("/plugin marketplace")[0].text
        assert "marketplaces: 1" in marketplace
        assert "demo-market:market-plugin" in marketplace

        blocked = controller.submit_prompt("/plugin install demo-market:market-plugin")[0].text
        assert "requires trust before install" in blocked

        trusted_source = controller.submit_prompt("/plugin trust-source demo-market:market-plugin on")[0].text
        assert "Plugin source trust updated: demo-market:market-plugin -> trusted." == trusted_source

        installed = controller.submit_prompt("/plugin install demo-market:market-plugin")[0].text
        assert "Installed marketplace plugin demo-market:market-plugin" in installed
        assert (workspace_root / ".claude" / "plugins" / "market-plugin").exists() is True

        validate = controller.submit_prompt("/plugin validate market-plugin")[0].text
        assert "Plugin validation:" in validate
        assert "manifest_name: market-plugin" in validate

        trust = controller.submit_prompt("/plugin trust market-plugin on")[0].text
        assert "Plugin trust updated: market-plugin -> trusted." == trust

        shown = controller.submit_prompt("/plugin marketplace show demo-market:market-plugin")[0].text
        assert "installed: yes" in shown
        assert "source_trusted: yes" in shown

        updated = controller.submit_prompt("/plugin update market-plugin")[0].text
        assert "Updated plugin market-plugin from demo-market:market-plugin." == updated

        listed = controller.submit_prompt("/plugin")[0].text
        assert "market-plugin | scope=project | trusted" in listed

        removed = controller.submit_prompt("/plugin remove market-plugin")[0].text
        assert "Removed plugin market-plugin." == removed
        assert (workspace_root / ".claude" / "plugins" / "market-plugin").exists() is False
    finally:
        controller.shutdown()


def test_mcp_command_lists_servers_and_tools(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "fake_mcp_server.py"
    )
    (workspace_root / ".mcp.json").write_text(
        (
            "{"
            '"mcpServers": {'
            '"fake": {'
            '"type": "stdio",'
            f'"command": "{sys.executable}",'
            f'"args": ["{fixture_path}"]'
            "}"
            "}"
            "}"
        ),
        encoding="utf-8",
    )

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        overview = controller.submit_prompt("/mcp")
        assert "fake | source=project | transport=stdio | status=connected | auth=ready | tools=1 | resources=0" in overview[0].text
        selector = controller.consume_requested_selector_dialog()
        assert selector is not None
        assert selector.kind == "selector:mcp"
        assert any(
            option.command == "/mcp show fake"
            for option in selector.options
        )

        tools = controller.submit_prompt("/mcp tools")
        assert "mcp__fake__echo_tool | server=fake | Echo MCP input" in tools[0].text

        details = controller.submit_prompt("/mcp show fake")
        assert "server_name: fake" in details[0].text
        assert "tools: echo_tool" in details[0].text

        registry = controller.submit_prompt("/mcp registry")
        assert "MCP registry snapshot:" in registry[0].text

        reconnect = controller.submit_prompt("/mcp reconnect fake")
        assert "Reconnected MCP server(s): fake" == reconnect[0].text
    finally:
        controller.shutdown()


def test_status_doctor_and_config_commands_report_runtime_snapshot(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        status = controller.submit_prompt("/status")
        assert "session_id: sess-1" in status[0].text
        assert "permission_mode: default" in status[0].text

        doctor = controller.submit_prompt("/doctor")
        assert "app_name=claude-code-py" in doctor[0].text
        assert "workspace_root=" in doctor[0].text

        config = controller.submit_prompt("/config")
        assert "Config snapshot:" in config[0].text
        assert "current_model: test-model" in config[0].text
    finally:
        controller.shutdown()


def test_plan_command_enables_plan_mode_and_can_show_plan_file(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        result = controller.submit_prompt("/plan review the architecture")
        assert controller.status_snapshot().permission_mode == "plan"
        assert result[-1].text == "assistant:review the architecture"

        plan_path = workspace_root / ".claude_code_py" / "plan.md"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text("# Plan\n- step one\n", encoding="utf-8")

        shown = controller.submit_prompt("/plan")
        assert "Current plan:" in shown[0].text
        assert "# Plan" in shown[0].text
    finally:
        controller.shutdown()


def test_export_command_writes_transcript_to_text_file(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        controller.submit_prompt("hello export")
        exported = controller.submit_prompt("/export notes/demo")
        assert "Conversation exported to:" in exported[0].text

        export_path = workspace_root / "notes" / "demo.txt"
        assert export_path.exists() is True
        content = export_path.read_text(encoding="utf-8")
        assert "User:" in content
        assert "hello export" in content
        assert "Claude:" in content
    finally:
        controller.shutdown()


def test_context_command_reports_current_message_snapshot(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        controller.submit_prompt("hello context")
        result = controller.submit_prompt("/context")
        assert "Context snapshot:" in result[0].text
        assert "message_count: 2" in result[0].text
        assert "last_user_message: hello context" in result[0].text
        assert "last_assistant_message: assistant:hello context" in result[0].text
    finally:
        controller.shutdown()


def test_session_command_reports_local_session_when_remote_is_unavailable(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        result = controller.submit_prompt("/session")
        assert "Not in remote mode." in result[0].text
        assert "current_session_id: sess-1" in result[0].text
    finally:
        controller.shutdown()


def test_session_remote_lifecycle_and_hydration_phase21(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)
    monkeypatch.setenv("CLAUDE_CODE_REMOTE_WORKER_TEST_MODE", "echo")

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        connected = controller.submit_prompt(
            "/session connect direct ws://127.0.0.1:9000/session/demo remote-1"
        )[0].text
        assert "Connected direct remote session:" in connected

        session_view = controller.submit_prompt("/session")[0].text
        assert "remote_mode: direct_connect" in session_view
        assert "remote_session_id: remote-1" in session_view

        heartbeat = controller.submit_prompt("/session heartbeat")[0].text
        assert "Remote heartbeat recorded." == heartbeat

        archive = controller.submit_prompt("/session archive")[0].text
        assert "Archived remote session remote-1" in archive

        history = controller.submit_prompt("/session history")[0].text
        assert "Archived remote sessions:" in history
        assert "remote-1" in history

        controller.submit_prompt("hydrate remote transcript")
        share_result = controller.submit_prompt("/share remote-share.json")[0].text
        assert "Share bundle written to:" in share_result
        bundle_path = workspace_root / "remote-share.json"
        assert bundle_path.exists() is True

        hydrated = controller.submit_prompt(f"/session hydrate {bundle_path}")[0].text
        assert "Hydrated remote transcript from" in hydrated

        hydrated_status = controller.submit_prompt("/status")[0].text
        assert "remote_mode: bridge" in hydrated_status
        assert "remote_hydrated_from:" in hydrated_status

        reconnect = controller.submit_prompt("/session reconnect")[0].text
        assert "Remote session reconnected: bridge" == reconnect
    finally:
        controller.shutdown()


def test_session_remote_send_events_and_permission_bridge_phase21(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = RemotePermissionProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)
    monkeypatch.setenv("CLAUDE_CODE_REMOTE_WORKER_TEST_MODE", "echo")

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1", ask_rules=["Write(path:*)"]),
        provider=provider,
    )

    try:
        connect = controller.submit_prompt(
            "/session connect direct ws://127.0.0.1:9000/session/demo remote-bridge"
        )[0].text
        assert "Connected direct remote session:" in connect

        queued = controller.submit_prompt("/session send hello remote")[0].text
        assert "Queued remote prompt as task" in queued

        waited = controller.submit_prompt("/session wait 2")[0].text
        assert "status: completed" in waited
        assert "result: remote:hello remote" in waited

        events = controller.submit_prompt("/session events")[0].text
        assert "Remote transcript:" in events
        assert "user: hello remote" in events
        assert "assistant: remote:hello remote" in events

        controller.submit_prompt("/session send remote write file")
        deadline = time() + 2
        pending = controller._command_context.remote_session_manager.pending_permission_requests()
        while not pending and time() < deadline:
            sleep(0.01)
            pending = controller._command_context.remote_session_manager.pending_permission_requests()
        requests_text = controller.submit_prompt("/session requests")[0].text
        assert "Pending remote permission requests:" in requests_text
        assert len(pending) == 1

        approved = controller.submit_prompt(f"/session approve {pending[0].request_id}")[0].text
        assert f"Approved remote permission request {pending[0].request_id}." == approved

        waited_after = controller.submit_prompt("/session wait 2")[0].text
        assert "status: completed" in waited_after
        assert "remote-finished" in waited_after

        events_after = controller.submit_prompt("/session events")[0].text
        assert "tool_use:Write" in events_after or "tool_use:Write {'file_path': 'remote.txt', 'content': 'hello remote'}" in events_after
        assert "assistant: remote-finished" in events_after
    finally:
        controller.shutdown()


def test_session_direct_websocket_transport_and_interrupt_phase21(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    remote_session_id = "remote-websocket"
    process, session_url = _start_remote_websocket_worker(
        container,
        workspace_root,
        remote_session_id=remote_session_id,
    )

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        connected = controller.submit_prompt(
            f"/session connect direct {session_url} {remote_session_id}"
        )[0].text
        assert "Connected direct remote session:" in connected
        assert "subprocess fallback" not in connected

        queued = controller.submit_prompt("/session send hello websocket")[0].text
        assert "Queued remote prompt as task" in queued

        waited = controller.submit_prompt("/session wait 2")[0].text
        assert "status: completed" in waited
        assert "result: remote:hello websocket" in waited

        controller.submit_prompt("/session send remote slow request")
        sleep(0.15)
        interrupted = controller.submit_prompt("/session interrupt")[0].text
        assert "Interrupted the active remote task." == interrupted

        waited_cancelled = controller.submit_prompt("/session wait 2")[0].text
        assert "status: cancelled" in waited_cancelled
        assert "Interrupted by user." in waited_cancelled

        events = controller.submit_prompt("/session events")[0].text
        assert "Remote events:" in events
        assert "transport=websocket" in events
        assert "status=cancelled" in events or "interrupt task_id=" in events
    finally:
        controller.shutdown()
        process.terminate()
        process.wait(timeout=5)


def test_rewind_command_can_remove_latest_turn_from_session(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        controller.submit_prompt("first turn")
        controller.submit_prompt("second turn")

        listed = controller.submit_prompt("/rewind")
        assert "Rewind points:" in listed[0].text
        assert "1 | files=0 | first turn" in listed[0].text
        assert "2 | files=0 | second turn" in listed[0].text

        rewound = controller.submit_prompt("/rewind last")
        assert "Rewound session before turn 2: second turn" in rewound[0].text
        assert len(controller._session_state.messages) == 2

        context_snapshot = controller.submit_prompt("/context")
        assert "message_count: 2" in context_snapshot[0].text
        assert "last_user_message: first turn" in context_snapshot[0].text
    finally:
        controller.shutdown()


def test_diff_command_reports_git_status_and_patch_stats(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    shell = controller_shell = None
    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        shell = controller._tool_context.shell_provider
        assert shell is not None
        shell.run("git init", cwd=workspace_root, timeout=10)
        shell.run("git config user.email test@example.com", cwd=workspace_root, timeout=10)
        shell.run("git config user.name test-user", cwd=workspace_root, timeout=10)
        tracked = workspace_root / "tracked.txt"
        tracked.write_text("alpha\n", encoding="utf-8")
        shell.run("git add tracked.txt", cwd=workspace_root, timeout=10)
        shell.run('git commit -m "init"', cwd=workspace_root, timeout=10)
        tracked.write_text("alpha\nbeta\n", encoding="utf-8")

        diff = controller.submit_prompt("/diff")
        assert "Git diff:" in diff[0].text
        assert "tracked.txt" in diff[0].text
        assert "Use /diff full to inspect the full patch." in diff[0].text

        full_diff = controller.submit_prompt("/diff full")
        assert "unstaged diff:" in full_diff[0].text
        assert "+beta" in full_diff[0].text
    finally:
        controller.shutdown()


def test_memory_command_lists_and_initializes_memory_files(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        listing = controller.submit_prompt("/memory")
        assert "Memory files:" in listing[0].text
        assert "user | exists=no" in listing[0].text
        assert "project | exists=no" in listing[0].text
        selector = controller.consume_requested_selector_dialog()
        assert selector is not None
        assert selector.kind == "selector:memory"
        assert any(
            option.command == "/memory edit project"
            for option in selector.options
        )

        init_result = controller.submit_prompt("/memory init project")
        assert "Initialized memory file at" in init_result[0].text

        project_memory = workspace_root / "CLAUDE.md"
        project_memory.write_text("project instructions", encoding="utf-8")
        shown = controller.submit_prompt("/memory show project")
        assert "Project memory:" in shown[0].text
        assert "project instructions" in shown[0].text
    finally:
        controller.shutdown()


def test_memory_extract_session_and_micro_compact_phase19(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        controller.submit_prompt("capture the architecture constraints")
        extracted = controller.submit_prompt("/memory extract session keep the key decisions")[0].text
        assert "Extracted session memory to:" in extracted
        session_memory_path = (
            container.paths.data_dir / "session_memory" / "sess-1.md"
        )
        assert session_memory_path.exists() is True
        assert "capture the architecture constraints" in session_memory_path.read_text(encoding="utf-8")

        controller.submit_prompt("second preserved turn")
        controller.submit_prompt("third preserved turn")
        compacted = controller.submit_prompt("/compact micro preserve the freshest turns")[0].text
        assert "Conversation micro-compacted." in compacted
        assert "mode: micro" in compacted
        assert len(controller._session_state.messages) >= 3
    finally:
        controller.shutdown()


def test_rewind_can_restore_file_history_phase19(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FileWriteProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1", permission_mode="bypass_permissions"),
        provider=provider,
    )

    try:
        controller.submit_prompt("write alpha")
        target = workspace_root / "notes.txt"
        assert target.read_text(encoding="utf-8") == "alpha"

        controller.submit_prompt("write beta")
        assert target.read_text(encoding="utf-8") == "beta"

        listed = controller.submit_prompt("/rewind")[0].text
        assert "files=1" in listed

        rewound = controller.submit_prompt("/rewind last")[0].text
        assert "files restored=1" in rewound
        assert target.read_text(encoding="utf-8") == "alpha"
    finally:
        controller.shutdown()


def test_share_sessions_and_session_background_phase19(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        controller.submit_prompt("share this session")
        assert (
            "Session backgrounding updated: on."
            == controller.submit_prompt("/session background on")[0].text
        )
        session_text = controller.submit_prompt("/session")[0].text
        assert "backgrounded: yes" in session_text
        assert "session_memory_path:" in session_text
        assert "file_history_snapshots:" in session_text

        sessions_text = controller.submit_prompt("/sessions")[0].text
        assert "Sessions:" in sessions_text
        assert "bg=yes" in sessions_text

        share_text = controller.submit_prompt("/share")[0].text
        assert "Share bundle written to:" in share_text
        share_dir = container.paths.data_dir / "shares"
        created = sorted(share_dir.glob("*.json"))
        assert created
        assert '"bundle_format": "claude-code-py-share-bundle"' in created[-1].read_text(encoding="utf-8")

        export_json_text = controller.submit_prompt("/export exports/session.json")[0].text
        assert "Conversation exported to:" in export_json_text
        export_path = workspace_root / "exports" / "session.json"
        assert export_path.exists() is True
        assert '"messages"' in export_path.read_text(encoding="utf-8")
    finally:
        controller.shutdown()


def test_hooks_command_reports_config_and_plugin_hook_declarations(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    plugin_root = tmp_path / "hook-plugin"
    monkeypatch.chdir(workspace_root)

    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    home_settings = fake_home / ".claude" / "settings.json"
    home_settings.parent.mkdir(parents=True, exist_ok=True)
    home_settings.write_text(
        '{"hooks":{"SessionStart":[{"command":"echo hi"}]}}',
        encoding="utf-8",
    )

    project_settings = workspace_root / ".claude" / "settings.json"
    project_settings.parent.mkdir(parents=True, exist_ok=True)
    project_settings.write_text(
        '{"hooks":{"PostToolUse":[{"command":"echo done"}]}}',
        encoding="utf-8",
    )

    (plugin_root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin_root / ".claude-plugin" / "plugin.json").write_text(
        (
            '{'
            '"name":"hook-plugin",'
            '"hooks":["./hooks/sample.json"]'
            '}'
        ),
        encoding="utf-8",
    )

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1", plugin_dirs=[str(plugin_root)]),
        provider=provider,
    )

    try:
        result = controller.submit_prompt("/hooks")
        assert "Hooks snapshot:" in result[0].text
        assert "SessionStart" in result[0].text
        assert "PostToolUse" in result[0].text
        assert "hook-plugin: ./hooks/sample.json" in result[0].text
    finally:
        controller.shutdown()


def test_stage16_preference_commands_update_runtime_state(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        assert "Theme preference updated to light." in controller.submit_prompt("/theme light")[0].text
        assert (
            "Output style preference updated to Learning."
            in controller.submit_prompt("/output-style Learning")[0].text
        )
        assert "Voice mode on." == controller.submit_prompt("/voice on")[0].text
        assert (
            "Default remote environment set to ubuntu-24.04."
            == controller.submit_prompt("/remote-env set ubuntu-24.04")[0].text
        )
        assert (
            "IDE auto-connect updated to on."
            == controller.submit_prompt("/ide auto-connect on")[0].text
        )
        assert (
            "Preferred IDE updated to ide."
            == controller.submit_prompt("/ide prefer ide")[0].text
        )
        assert (
            "Sandbox preference updated: enabled=on."
            == controller.submit_prompt("/sandbox-toggle on")[0].text
        )
        assert (
            "Sandbox preference updated: auto-allow=on."
            == controller.submit_prompt("/sandbox auto-allow on")[0].text
        )

        prefs = controller._command_context.runtime_state_store.get_preferences()
        assert prefs.theme == "light"
        assert prefs.output_style == "Learning"
        assert prefs.voice_enabled is True
        assert prefs.default_remote_environment == "ubuntu-24.04"
        assert prefs.ide_auto_connect is True
        assert prefs.preferred_ide == "ide"
        assert prefs.sandbox_enabled is True
        assert prefs.sandbox_auto_allow is True

        config = controller.submit_prompt("/config")[0].text
        assert "theme: light" in config
        assert "output_style: Learning" in config
        assert "voice_enabled: True" in config
    finally:
        controller.shutdown()


def test_stage16_cost_compact_and_tag_commands_are_functional(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        controller.submit_prompt("track usage")
        cost = controller.submit_prompt("/cost")[0].text
        assert "requests: 1" in cost
        assert "input_tokens: 11" in cost
        assert "output_tokens: 7" in cost

        assert (
            "Tagged the current session with #bugfix."
            == controller.submit_prompt("/tag bugfix")[0].text
        )
        status = controller.submit_prompt("/status")[0].text
        assert "tag: bugfix" in status

        resume_listing = controller.submit_prompt("/resume")[0].text
        assert "#bugfix" in resume_listing

        compact = controller.submit_prompt("/compact keep the important decisions")[0].text
        assert "Conversation compacted." in compact
        assert len(controller._session_state.messages) == 2
        assert controller._session_state.messages[0].content.startswith("Conversation summary:")
        assert "keep the important decisions" in controller._session_state.messages[0].content

        assert (
            "Removed tag #bugfix from the current session."
            == controller.submit_prompt("/tag bugfix")[0].text
        )
    finally:
        controller.shutdown()


def test_stage16_auth_agents_mobile_and_desktop_commands(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    plugin_root = tmp_path / "agent-plugin"
    monkeypatch.chdir(workspace_root)

    (plugin_root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin_root / ".claude-plugin" / "plugin.json").write_text(
        (
            '{'
            '"name":"agent-plugin",'
            '"agents":["./agents"]'
            '}'
        ),
        encoding="utf-8",
    )

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1", plugin_dirs=[str(plugin_root)]),
        provider=provider,
    )

    try:
        login = controller.submit_prompt("/login api-key sk-test")[0].text
        assert "Configured ANTHROPIC_API_KEY" in login
        env_text = container.paths.env_file.read_text(encoding="utf-8")
        assert "ANTHROPIC_API_KEY=sk-test" in env_text
        assert container.settings.anthropic_api_key == "sk-test"

        logout = controller.submit_prompt("/logout")[0].text
        assert "Cleared ANTHROPIC_API_KEY" in logout
        assert container.settings.anthropic_api_key is None

        agents = controller.submit_prompt("/agents")[0].text
        assert "Agents overview:" in agents
        assert "plugin_agent_paths: 1" in agents
        assert "agent-plugin: ./agents" in agents

        ide = controller.submit_prompt("/ide")[0].text
        assert "IDE integration:" in ide

        mobile = controller.submit_prompt("/mobile")[0].text
        assert "Claude mobile app:" in mobile
        assert "apps.apple.com" in mobile

        desktop = controller.submit_prompt("/desktop")[0].text
        assert "Claude Desktop handoff:" in desktop
        assert "transcript_path:" in desktop
    finally:
        controller.shutdown()


def test_command_parity_aliases_and_new_local_commands(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        config_text = controller.submit_prompt("/settings")[0].text
        assert "Config snapshot:" in config_text

        permissions_text = controller.submit_prompt("/allowed-tools")[0].text
        assert "Permissions:" in permissions_text

        assert "Advisor set to opus." == controller.submit_prompt("/advisor opus")[0].text
        assert "Set effort level to high." == controller.submit_prompt("/effort high")[0].text
        assert "Fast mode on." == controller.submit_prompt("/fast on")[0].text

        branch_text = controller.submit_prompt("/fork feature branch")[0].text
        assert "Created branched session" in branch_text
        assert controller._session_state.metadata.parent_session_id == "sess-1"
        assert controller._session_state.metadata.title == "feature branch"

        feedback_text = controller.submit_prompt("/bug the prompt overlay still jumps")[0].text
        assert "Recorded feedback in" in feedback_text
        feedback_log = container.paths.data_dir / "feedback.log"
        assert feedback_log.exists() is True
        assert "the prompt overlay still jumps" in feedback_log.read_text(encoding="utf-8")
    finally:
        controller.shutdown()


def test_team_and_tasks_phase20(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        created = controller.submit_prompt("/team create alpha-team coordination crew")[0].text
        assert "Created team alpha-team." == created

        spawned = controller.submit_prompt("/team spawn researcher investigate dependencies")[0].text
        assert "Spawned teammate researcher in team alpha-team." in spawned

        mailbox = controller.submit_prompt("/team message researcher hello teammate")[0].text
        assert "Sent message to researcher." == mailbox

        mailbox_view = controller.submit_prompt("/team mailbox researcher")[0].text
        assert "Mailbox: researcher" in mailbox_view
        assert "hello teammate" in mailbox_view

        tasks_text = controller.submit_prompt("/tasks")[0].text
        assert "teammate" in tasks_text

        task_id = controller._task_service.list_tasks()[0].task_id
        task_show = controller.submit_prompt(f"/tasks show {task_id}")[0].text
        assert "kind: teammate" in task_show
        task_output = controller.submit_prompt(f"/tasks output {task_id}")[0].text
        assert f"task_id: {task_id}" in task_output

        updated = controller.submit_prompt(f"/tasks update {task_id} owner planner")[0].text
        assert f"Updated task {task_id}: owner=planner" == updated

        agents = controller.submit_prompt("/agents")[0].text
        assert "active_team: alpha-team" in agents

        stopped = controller.submit_prompt("/team stop researcher")[0].text
        assert "Stopped teammate researcher." == stopped
    finally:
        controller.shutdown()


def test_add_dir_command_extends_tool_path_resolution(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    outside_root = tmp_path / "shared"
    outside_root.mkdir(parents=True, exist_ok=True)
    target = outside_root / "notes.txt"
    target.write_text("shared context", encoding="utf-8")
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        added = controller.submit_prompt(f"/add-dir {outside_root}")[0].text
        assert "Added" in added
        read_result = FileReadTool().execute(
            FileReadToolInput(file_path=str(target)),
            controller._tool_context,
        )
        assert read_result.output == "shared context"
    finally:
        controller.shutdown()


def test_new_prompt_commands_route_to_provider(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = _workspace_root(container)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        controller.submit_prompt("/statusline custom shell prompt")
        controller.submit_prompt("/security-review")
        controller.submit_prompt("/pr-comments 123")

        prompts = [request.messages[-1].content for request in provider.requests]
        assert any("custom shell prompt" in prompt for prompt in prompts)
        assert any("focused security review" in prompt.lower() for prompt in prompts)
        assert any("GitHub pull request" in prompt for prompt in prompts)
    finally:
        controller.shutdown()


def _workspace_root(container) -> Path:
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    return workspace_root


def _start_remote_websocket_worker(
    container,
    workspace_root: Path,
    *,
    remote_session_id: str,
) -> tuple[subprocess.Popen[str], str]:
    env = os.environ.copy()
    env["CLAUDE_CODE_REMOTE_WORKER_TEST_MODE"] = "echo"
    env["CLAUDE_CODE_REMOTE_WORKER_SESSION_ID"] = remote_session_id
    env["CLAUDE_CODE_REMOTE_WORKER_MODEL"] = container.settings.default_model
    env["CLAUDE_CODE_REMOTE_WORKER_SYSTEM_PROMPT"] = ""
    env["CLAUDE_CODE_REMOTE_WORKER_WORKSPACE_ROOT"] = str(workspace_root)
    env["CLAUDE_CODE_REMOTE_WORKER_PROJECT_ROOT"] = str(container.paths.root)
    env["CLAUDE_CODE_REMOTE_WORKER_DATA_DIR"] = str(container.paths.data_dir)
    env["CLAUDE_CODE_REMOTE_WORKER_SESSIONS_DIR"] = str(container.paths.sessions_dir)
    env["CLAUDE_CODE_REMOTE_WORKER_SESSION_INDEX"] = str(container.paths.session_index_path)
    env["CLAUDE_CODE_REMOTE_WORKER_ENV_FILE"] = str(container.paths.env_file)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "claude_code_py.providers.remote.worker",
            "--websocket-server",
            "127.0.0.1",
            "0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        cwd=str(workspace_root),
        env=env,
    )
    assert process.stdout is not None
    line = process.stdout.readline()
    payload = json.loads(line)
    return process, f"ws://{payload['host']}:{payload['port']}/session/{remote_session_id}"
