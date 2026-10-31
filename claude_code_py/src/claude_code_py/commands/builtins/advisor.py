from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_advisor_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        arg = invocation.args.strip().lower()
        prefs = context.runtime_state_store.get_preferences()
        current = prefs.advisor_model

        if not arg:
            if not current:
                return CommandResult(
                    kind="message",
                    message=(
                        'Advisor: not set\n'
                        'Use "/advisor <model>" to enable or "/advisor off" to disable.'
                    ),
                )
            return CommandResult(
                kind="message",
                message=(
                    f"Advisor: {current}\n"
                    'Use "/advisor off" to disable or "/advisor <model>" to change.'
                ),
            )

        if arg in {"off", "unset"}:
            if current is None:
                return CommandResult(kind="message", message="Advisor already unset.")
            context.runtime_state_store.update_preferences(advisor_model=None)
            return CommandResult(
                kind="message",
                message=f"Advisor disabled (was {current}).",
            )

        context.runtime_state_store.update_preferences(advisor_model=arg)
        return CommandResult(
            kind="message",
            message=f"Advisor set to {arg}.",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="advisor",
            description="Configure the advisor model.",
            command_type="local_ui",
            argument_hint="[<model>|off]",
        ),
        usage="/advisor [<model>|off]",
        handler=handler,
    )
