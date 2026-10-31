from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_thinkback_play_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context, invocation
        return CommandResult(
            kind="message",
            message="Thinkback animation playback is not available in the Python rebuild.",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="thinkback-play",
            description="Play the thinkback animation.",
            command_type="local_ui",
        ),
        usage="/thinkback-play",
        handler=handler,
        hidden=True,
    )
