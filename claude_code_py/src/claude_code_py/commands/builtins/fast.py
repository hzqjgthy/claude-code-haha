from claude_code_py.commands.builtins._helpers import bool_word
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_fast_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.strip().lower()
        prefs = context.runtime_state_store.get_preferences()

        if args in {"", "status"}:
            return CommandResult(
                kind="message",
                message=f"Fast mode: {bool_word(prefs.fast_mode)}",
            )

        if args not in {"on", "off"}:
            return CommandResult(
                kind="error",
                message="Usage: /fast [on|off]",
            )

        enabled = args == "on"
        context.runtime_state_store.update_preferences(fast_mode=enabled)
        return CommandResult(
            kind="message",
            message=f"Fast mode {bool_word(enabled)}.",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="fast",
            description="Toggle fast mode.",
            command_type="local_ui",
            argument_hint="[on|off]",
        ),
        usage="/fast [on|off]",
        handler=handler,
    )
