from claude_code_py.commands.builtins._helpers import THEME_OPTIONS
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_theme_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        requested = invocation.args.strip()
        prefs = context.runtime_state_store.get_preferences()
        if not requested or requested in {"current", "show", "list"}:
            lines = [
                "Theme settings:",
                f"current_theme: {prefs.theme}",
                f"available: {', '.join(THEME_OPTIONS)}",
                "Use /theme <name> to update the preferred theme.",
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:theme",
                dialog_title="Theme",
                dialog_lines=lines,
                selector_kind="selector:theme",
                selector_title="Choose Theme",
                selector_options=[
                    CommandSelectorOption(
                        label=option,
                        command=f"/theme {option}",
                        description="current" if option == prefs.theme else None,
                    )
                    for option in THEME_OPTIONS
                ],
            )

        if requested not in THEME_OPTIONS:
            return CommandResult(
                kind="error",
                message=(
                    "Unknown theme. "
                    f"Expected one of: {', '.join(THEME_OPTIONS)}"
                ),
            )
        context.runtime_state_store.update_preferences(theme=requested)
        return CommandResult(
            kind="message",
            message=(
                f"Theme preference updated to {requested}. "
                "A fresh UI session will use the new theme."
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="theme",
            description="Show or change the preferred terminal theme.",
            command_type="local_ui",
            argument_hint="[theme]",
        ),
        usage="/theme [auto|dark|light|light-daltonized|dark-daltonized|light-ansi|dark-ansi]",
        handler=handler,
    )
