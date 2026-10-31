from claude_code_py.commands.builtins._helpers import try_open_url
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

UPGRADE_URL = "https://claude.ai/upgrade/max"


def build_upgrade_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context, invocation
        opened = try_open_url(UPGRADE_URL)
        return CommandResult(
            kind="message",
            message=(
                "Opening Max upgrade page. After upgrading, run /login to refresh your session."
                if opened
                else f"Failed to open browser. Please visit {UPGRADE_URL}."
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="upgrade",
            description="Upgrade to Max for higher rate limits and more Opus.",
            command_type="local_ui",
        ),
        usage="/upgrade",
        handler=handler,
    )
