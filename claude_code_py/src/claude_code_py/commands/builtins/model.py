from claude_code_py.commands.loader import CommandContext, CommandResult, SlashCommand, SlashCommandInvocation
from claude_code_py.domain.commands import CommandSpec


def build_model_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        requested_model = invocation.args.strip()
        if not requested_model:
            return CommandResult(
                kind="message",
                message=f"Current model: {context.model_name}",
            )
        context.model_name = requested_model
        context.bind_status()
        return CommandResult(
            kind="message",
            message=f"Model updated to {context.model_name}",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="model",
            description="Show or change the current model.",
            command_type="local",
            argument_hint="[model]",
        ),
        usage="/model [model]",
        handler=handler,
    )
