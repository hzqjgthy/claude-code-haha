import os
import platform

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_terminal_setup_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        prefs = context.runtime_state_store.get_preferences()
        terminal = os.environ.get("TERM_PROGRAM") or os.environ.get("TERM") or "(unknown)"
        system = platform.system()
        lines = [
            "Terminal setup",
            f"platform: {system}",
            f"terminal: {terminal}",
            f"setup_marked_complete: {prefs.terminal_setup_complete}",
            "",
            "Goal: enable a convenient Shift+Enter-style multiline workflow.",
            "If your terminal already supports Shift+Enter natively, no extra setup is needed.",
            "Otherwise configure a send-sequence binding in your terminal or IDE terminal.",
            "",
            "Run /terminal-setup done to mark the setup as complete.",
        ]
        arg = invocation.args.strip().lower()
        if arg == "done":
            context.runtime_state_store.update_preferences(terminal_setup_complete=True)
            return CommandResult(
                kind="message",
                message="Marked terminal setup as complete.",
            )
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:terminal-setup",
            dialog_title="Terminal Setup",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="terminal-setup",
            description="Install Shift+Enter key binding guidance for multiline prompts.",
            command_type="local_ui",
        ),
        usage="/terminal-setup",
        handler=handler,
    )
