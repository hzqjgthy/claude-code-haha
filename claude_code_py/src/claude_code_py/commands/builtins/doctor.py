from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_doctor_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        settings = context.container.settings
        paths = context.container.paths
        api_key_configured = bool(getattr(settings, "anthropic_api_key", None))
        auth_token_configured = bool(getattr(settings, "anthropic_auth_token", None))
        transcript_path = paths.sessions_dir / f"{context.session_state.metadata.session_id}.jsonl"
        remote = context.remote_provider.status() if context.remote_provider else None
        remote_request_count = (
            len(context.remote_session_manager.pending_permission_requests())
            if context.remote_session_manager is not None
            else 0
        )
        lines = [
            "Doctor:",
            f"app_name={settings.app_name}",
            f"project_root={paths.root}",
            f"workspace_root={context.workspace_root}",
            f"data_dir={paths.data_dir}",
            f"session_index={paths.session_index_path}",
            f"transcript_path={transcript_path}",
            f"current_model={context.model_name}",
            f"default_model={settings.default_model}",
            f"anthropic_base_url={getattr(settings, 'anthropic_base_url', '(unknown)')}",
            f"api_key_configured={'yes' if api_key_configured else 'no'}",
            f"auth_token_configured={'yes' if auth_token_configured else 'no'}",
            f"permission_mode={context.permission_mode}",
            f"plugin_count={len(context.plugins)}",
            f"skill_count={len(context.skills)}",
            f"mcp_server_count={len(context.mcp_server_configs)}",
            f"mcp_error_count={len(context.mcp_manager.errors)}",
        ]
        if remote is not None:
            lines.extend(
                [
                    f"remote_mode={remote.mode}",
                    f"remote_connected={'yes' if remote.connected else 'no'}",
                    f"remote_transport={remote.transport}",
                    f"remote_session_id={remote.remote_session_id or '(none)'}",
                    f"remote_detail={remote.detail or '(none)'}",
                    f"remote_can_reconnect={'yes' if remote.can_reconnect else 'no'}",
                    f"remote_pending_requests={remote_request_count}",
                ]
            )
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:doctor",
            dialog_title="Doctor",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="doctor",
            description="Inspect environment, storage, auth, and runtime health.",
            command_type="local_ui",
        ),
        usage="/doctor",
        handler=handler,
    )
