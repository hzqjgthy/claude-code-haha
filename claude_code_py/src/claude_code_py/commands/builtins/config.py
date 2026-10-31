from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_config_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        settings = context.container.settings
        paths = context.container.paths
        prefs = context.runtime_state_store.get_preferences()
        lines = [
            "Config snapshot:",
            f"app_name: {settings.app_name}",
            f"project_root: {paths.root}",
            f"workspace_root: {context.workspace_root}",
            f"data_dir: {paths.data_dir}",
            f"sessions_dir: {paths.sessions_dir}",
            f"env_file: {paths.env_file}",
            f"default_model: {settings.default_model}",
            f"current_model: {context.model_name}",
            f"permission_mode: {context.permission_mode}",
            f"theme: {prefs.theme}",
            f"output_style: {prefs.output_style}",
            f"voice_enabled: {prefs.voice_enabled}",
            f"editor_mode: {prefs.editor_mode}",
            f"fast_mode: {prefs.fast_mode}",
            f"effort_level: {prefs.effort_level or 'auto'}",
            f"advisor_model: {prefs.advisor_model or '(none)'}",
            f"copy_full_response: {prefs.copy_full_response}",
            f"statusline_enabled: {prefs.statusline_enabled}",
            f"chrome_enabled_by_default: {prefs.chrome_enabled_by_default}",
            f"terminal_setup_complete: {prefs.terminal_setup_complete}",
            f"extra_usage_enabled: {prefs.extra_usage_enabled}",
            (
                "default_remote_environment: "
                f"{prefs.default_remote_environment or '(none)'}"
            ),
            f"ide_auto_connect: {prefs.ide_auto_connect}",
            f"preferred_ide: {prefs.preferred_ide or '(none)'}",
            f"sandbox_enabled: {prefs.sandbox_enabled}",
            (
                "working_directories: "
                + ", ".join(str(root) for root in context.tool_context.allowed_roots())
            ),
            f"system_prompt_configured: {'yes' if context.base_system_prompt else 'no'}",
            f"auth_api_key_configured: {'yes' if settings.anthropic_api_key else 'no'}",
            (
                "auth_token_configured: "
                f"{'yes' if settings.anthropic_auth_token else 'no'}"
            ),
            f"plugin_dirs: {', '.join(context.plugin_dirs) or '(none)'}",
            f"loaded_plugins: {len(context.plugins)}",
            f"loaded_skills: {len(context.skills)}",
            f"mcp_server_configs: {len(context.mcp_server_configs)}",
            f"mcp_tools: {len(context.mcp_tool_definitions)}",
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:config",
            dialog_title="Config",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="config",
            description="Show the current runtime configuration snapshot.",
            command_type="local_ui",
            aliases=["settings"],
        ),
        usage="/config",
        handler=handler,
    )
