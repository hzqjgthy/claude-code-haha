from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_reload_plugins_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        skills = context.reload_skills()
        plugin_count = len(context.plugins)
        skill_count = len(skills)
        command_count = len(context.command_registry.list_commands())
        error_count = len(context.plugin_errors)
        message = (
            "Reloaded: "
            f"{plugin_count} plugin(s) · {skill_count} skill(s) · "
            f"{command_count} command(s)"
        )
        if error_count > 0:
            message += f"\n{error_count} load error(s). Run /doctor for details."
        return CommandResult(
            kind="message",
            message=message,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="reload-plugins",
            description="Activate pending plugin changes in the current session.",
            command_type="local_ui",
        ),
        usage="/reload-plugins",
        handler=handler,
    )
