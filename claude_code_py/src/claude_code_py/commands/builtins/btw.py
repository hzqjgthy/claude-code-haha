from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_btw_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context
        question = invocation.args.strip()
        if not question:
            return CommandResult(
                kind="error",
                message="Usage: /btw <your question>",
            )
        return CommandResult(
            kind="prompt",
            prompt=(
                "Quick side question. Answer briefly without derailing the main task:\n\n"
                f"{question}"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="btw",
            description="Ask a quick side question without interrupting the main conversation.",
            command_type="prompt",
            argument_hint="<question>",
        ),
        usage="/btw <question>",
        handler=handler,
    )
