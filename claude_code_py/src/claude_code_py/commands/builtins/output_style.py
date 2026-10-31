from claude_code_py.commands.builtins._helpers import OUTPUT_STYLE_OPTIONS
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_output_style_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        requested = invocation.args.strip()
        prefs = context.runtime_state_store.get_preferences()
        if not requested:
            return CommandResult(
                kind="message",
                message=(
                    "/output-style has been deprecated. "
                    "Use /config to inspect it or /output-style <style> to update "
                    "the preference for the next session.\n"
                    f"current_output_style: {prefs.output_style}\n"
                    f"available: {', '.join(OUTPUT_STYLE_OPTIONS)}"
                ),
            )
        if requested not in OUTPUT_STYLE_OPTIONS:
            return CommandResult(
                kind="error",
                message=(
                    "Unknown output style. "
                    f"Expected one of: {', '.join(OUTPUT_STYLE_OPTIONS)}"
                ),
            )
        context.runtime_state_store.update_preferences(output_style=requested)
        return CommandResult(
            kind="message",
            message=(
                f"Output style preference updated to {requested}. "
                "Changes take effect on the next session."
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="output-style",
            description="Deprecated: use /config to inspect output style preferences.",
            command_type="local",
            argument_hint="[style]",
        ),
        usage="/output-style [default|Explanatory|Learning]",
        handler=handler,
        hidden=True,
    )
