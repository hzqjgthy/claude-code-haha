from pathlib import Path

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.tools.file_context import list_file_context_paths


def build_status_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        metadata = context.session_state.metadata
        remote = context.remote_provider.status() if context.remote_provider else None
        remote_request_count = (
            len(context.remote_session_manager.pending_permission_requests())
            if context.remote_session_manager is not None
            else 0
        )
        messages = context.session_state.messages
        transcript_path = context.container.paths.sessions_dir / f"{metadata.session_id}.jsonl"
        session_tag = context.runtime_state_store.get_session_tag(metadata.session_id)
        session_color = context.runtime_state_store.get_session_color(metadata.session_id)
        prefs = context.runtime_state_store.get_preferences()
        user_messages = sum(1 for message in messages if message.kind == "user")
        assistant_messages = sum(1 for message in messages if message.kind == "assistant")
        tool_messages = sum(1 for message in messages if message.kind.startswith("tool_"))
        file_count = len(list_file_context_paths(context.tool_context))
        task_count = len(context.task_service.list_tasks())

        lines = [
            "Status:",
            f"session_id: {metadata.session_id}",
            f"title: {metadata.title}",
            f"parent_session_id: {metadata.parent_session_id or '(none)'}",
            f"status: {metadata.status}",
            f"created_at: {metadata.created_at.isoformat(timespec='seconds')}",
            f"updated_at: {metadata.updated_at.isoformat(timespec='seconds')}",
            f"model: {context.model_name}",
            f"permission_mode: {context.permission_mode}",
            f"tag: {session_tag or '(none)'}",
            f"color: {session_color or 'default'}",
            f"workspace_root: {context.workspace_root}",
            f"cwd: {context.tool_context.cwd}",
            (
                "working_directories: "
                + ", ".join(str(root) for root in context.tool_context.allowed_roots())
            ),
            f"transcript_path: {transcript_path}",
            f"message_count: {len(messages)}",
            f"user_messages: {user_messages}",
            f"assistant_messages: {assistant_messages}",
            f"tool_messages: {tool_messages}",
            f"task_count: {task_count}",
            f"files_in_context: {file_count}",
            f"editor_mode: {prefs.editor_mode}",
            f"fast_mode: {prefs.fast_mode}",
            f"effort_level: {prefs.effort_level or 'auto'}",
            f"statusline_enabled: {prefs.statusline_enabled}",
            f"plugin_count: {len(context.plugins)}",
            f"skill_count: {len(context.skills)}",
            f"mcp_server_count: {len(context.mcp_server_configs)}",
            f"mcp_tool_count: {len(context.mcp_tool_definitions)}",
        ]
        if remote is not None:
            lines.extend(
                [
                    f"remote_mode: {remote.mode}",
                    f"remote_connected: {'yes' if remote.connected else 'no'}",
                    f"remote_transport: {remote.transport}",
                    f"remote_session_id: {remote.remote_session_id or '(none)'}",
                    f"remote_detail: {remote.detail or '(none)'}",
                    f"remote_session_url: {remote.session_url or '(none)'}",
                    f"remote_can_reconnect: {remote.can_reconnect}",
                    "remote_last_heartbeat: "
                    f"{remote.last_heartbeat_at.isoformat(timespec='seconds') if remote.last_heartbeat_at else '(none)'}",
                    f"remote_hydrated_from: {remote.hydrated_from or '(none)'}",
                    f"remote_pending_requests: {remote_request_count}",
                ]
            )
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:status",
            dialog_title="Status",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="status",
            description="Show the current session and runtime status snapshot.",
            command_type="local_ui",
        ),
        usage="/status",
        handler=handler,
    )
