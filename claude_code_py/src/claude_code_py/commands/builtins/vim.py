from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_vim_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        prefs = context.runtime_state_store.get_preferences()
        current = prefs.editor_mode if prefs.editor_mode in {"normal", "vim"} else "normal"
        next_mode = "vim" if current == "normal" else "normal"
        context.runtime_state_store.update_preferences(editor_mode=next_mode)
        return CommandResult(
            kind="message",
            message=(
                f"Editor mode set to {next_mode}. "
                + (
                    "Use Escape to toggle between INSERT and NORMAL modes."
                    if next_mode == "vim"
                    else "Using standard keyboard bindings."
                )
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="vim",
            description="Toggle between Vim and Normal editing modes.",
            command_type="local_ui",
        ),
        usage="/vim",
        handler=handler,
    )
