from claude_code_py.commands.builtins._helpers import bool_word, try_open_url
from claude_code_py.commands.loader import (
    CommandContext,
    CommandDialogAction,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

CHROME_EXTENSION_URL = "https://claude.ai/chrome"
CHROME_PERMISSIONS_URL = "https://clau.de/chrome/permissions"
CHROME_RECONNECT_URL = "https://clau.de/chrome/reconnect"
CHROME_DOCS_URL = "https://code.claude.com/docs/en/chrome"


def build_chrome_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        arg = invocation.args.strip().lower()
        prefs = context.runtime_state_store.get_preferences()

        if arg in {"toggle-default", "toggle"}:
            next_value = not prefs.chrome_enabled_by_default
            context.runtime_state_store.update_preferences(
                chrome_enabled_by_default=next_value,
            )
            return CommandResult(
                kind="message",
                message=f"Claude in Chrome default mode {bool_word(next_value)}.",
            )

        if arg in {"install-extension", "install"}:
            opened = try_open_url(CHROME_EXTENSION_URL)
            return CommandResult(
                kind="message",
                message=(
                    "Opening Chrome extension page..."
                    if opened
                    else f"Open this URL in your browser: {CHROME_EXTENSION_URL}"
                ),
            )

        if arg in {"manage-permissions", "permissions"}:
            opened = try_open_url(CHROME_PERMISSIONS_URL)
            return CommandResult(
                kind="message",
                message=(
                    "Opening Chrome permissions page..."
                    if opened
                    else f"Open this URL in your browser: {CHROME_PERMISSIONS_URL}"
                ),
            )

        if arg == "reconnect":
            opened = try_open_url(CHROME_RECONNECT_URL)
            return CommandResult(
                kind="message",
                message=(
                    "Opening Chrome reconnect page..."
                    if opened
                    else f"Open this URL in your browser: {CHROME_RECONNECT_URL}"
                ),
            )

        lines = [
            "Claude in Chrome (Beta)",
            f"enabled_by_default: {bool_word(prefs.chrome_enabled_by_default)}",
            f"docs: {CHROME_DOCS_URL}",
            "Available actions: install-extension, reconnect, manage-permissions, toggle-default",
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:chrome",
            dialog_title="Claude in Chrome",
            dialog_lines=lines,
            dialog_actions=[
                CommandDialogAction(
                    label="Install Extension",
                    command="/chrome install-extension",
                ),
                CommandDialogAction(
                    label="Reconnect",
                    command="/chrome reconnect",
                ),
                CommandDialogAction(
                    label="Permissions",
                    command="/chrome manage-permissions",
                ),
                CommandDialogAction(
                    label="Toggle Default",
                    command="/chrome toggle-default",
                ),
            ],
        )

    return SlashCommand(
        spec=CommandSpec(
            name="chrome",
            description="Claude in Chrome (Beta) settings.",
            command_type="local_ui",
            argument_hint="[install-extension|reconnect|manage-permissions|toggle-default]",
        ),
        usage="/chrome [install-extension|reconnect|manage-permissions|toggle-default]",
        handler=handler,
    )
