from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

FALLBACK_MESSAGE = (
    "Review and manage your privacy settings at "
    "https://claude.ai/settings/data-privacy-controls"
)


def build_privacy_settings_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context, invocation
        return CommandResult(kind="message", message=FALLBACK_MESSAGE)

    return SlashCommand(
        spec=CommandSpec(
            name="privacy-settings",
            description="View and update your privacy settings.",
            command_type="local_ui",
        ),
        usage="/privacy-settings",
        handler=handler,
    )
