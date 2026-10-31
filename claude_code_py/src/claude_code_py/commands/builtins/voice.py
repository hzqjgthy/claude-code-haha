from claude_code_py.commands.builtins._helpers import bool_word
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_voice_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        prefs = context.runtime_state_store.get_preferences()
        arg = invocation.args.strip().lower()
        if arg == "status":
            return CommandResult(
                kind="message",
                message=f"Voice mode is currently {bool_word(prefs.voice_enabled)}.",
            )
        if arg in {"on", "off"}:
            enabled = arg == "on"
        else:
            enabled = not prefs.voice_enabled
        context.runtime_state_store.update_preferences(voice_enabled=enabled)
        return CommandResult(
            kind="message",
            message=f"Voice mode {bool_word(enabled)}.",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="voice",
            description="Toggle the persisted voice-mode preference.",
            command_type="local",
            argument_hint="[status|on|off]",
        ),
        usage="/voice [status|on|off]",
        handler=handler,
    )
