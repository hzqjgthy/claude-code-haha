from claude_code_py.commands.builtins._helpers import bool_word, try_open_url
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

EXTRA_USAGE_URL = "https://claude.ai/settings/billing"


def build_extra_usage_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        arg = invocation.args.strip().lower()
        prefs = context.runtime_state_store.get_preferences()
        if arg in {"", "status"}:
            return CommandResult(
                kind="message",
                message=(
                    "Extra usage configuration\n"
                    f"enabled: {bool_word(prefs.extra_usage_enabled)}\n"
                    f"billing_url: {EXTRA_USAGE_URL}"
                ),
            )
        if arg in {"on", "enable"}:
            context.runtime_state_store.update_preferences(extra_usage_enabled=True)
            opened = try_open_url(EXTRA_USAGE_URL)
            return CommandResult(
                kind="message",
                message=(
                    "Extra usage enabled in local preferences and billing page opened."
                    if opened
                    else f"Extra usage enabled in local preferences. Visit: {EXTRA_USAGE_URL}"
                ),
            )
        if arg in {"off", "disable"}:
            context.runtime_state_store.update_preferences(extra_usage_enabled=False)
            return CommandResult(kind="message", message="Extra usage disabled.")
        return CommandResult(
            kind="error",
            message="Usage: /extra-usage [status|on|off]",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="extra-usage",
            description="Configure extra usage to keep working when limits are hit.",
            command_type="local_ui",
        ),
        usage="/extra-usage [status|on|off]",
        handler=handler,
    )
