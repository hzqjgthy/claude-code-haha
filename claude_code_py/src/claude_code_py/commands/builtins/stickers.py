from claude_code_py.commands.builtins._helpers import try_open_url
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

STICKERS_URL = "https://www.stickermule.com/claudecode"


def build_stickers_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context, invocation
        opened = try_open_url(STICKERS_URL)
        return CommandResult(
            kind="message",
            message=(
                "Opening sticker page in browser..."
                if opened
                else f"Failed to open browser. Visit: {STICKERS_URL}"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="stickers",
            description="Order Claude Code stickers.",
            command_type="local_ui",
        ),
        usage="/stickers",
        handler=handler,
    )
