from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_statusline_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context
        prompt = (
            invocation.args.strip()
            or "Configure my statusLine from my shell PS1 configuration"
        )
        return CommandResult(
            kind="prompt",
            prompt=(
                "Create an agent-based status line setup plan for this request:\n\n"
                f"{prompt}"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="statusline",
            description="Set up Claude Code's status line UI.",
            command_type="prompt",
            argument_hint="[request]",
        ),
        usage="/statusline [request]",
        handler=handler,
    )
