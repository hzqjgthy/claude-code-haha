from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_exit_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context, invocation
        return CommandResult(
            kind="message",
            message="Goodbye!",
            terminate_session=True,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="exit",
            description="Exit the REPL.",
            command_type="local_ui",
            aliases=["quit"],
        ),
        usage="/exit",
        handler=handler,
    )
