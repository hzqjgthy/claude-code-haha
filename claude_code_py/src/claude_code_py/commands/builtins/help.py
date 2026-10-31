from claude_code_py.commands.loader import CommandContext, CommandResult, SlashCommand, SlashCommandInvocation
from claude_code_py.domain.commands import CommandSpec


def build_help_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        lines = ["Available commands:"]
        for command in context.command_registry.list_commands():
            if command.hidden:
                continue
            lines.append(
                f"/{command.spec.name} - {command.spec.description} [{command.source}]",
            )
            lines.append(f"  usage: {command.usage}")
        return CommandResult(kind="message", message="\n".join(lines))

    return SlashCommand(
        spec=CommandSpec(
            name="help",
            description="Show available slash commands.",
            command_type="local_ui",
        ),
        usage="/help",
        handler=handler,
    )
