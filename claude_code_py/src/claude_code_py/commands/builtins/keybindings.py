from pathlib import Path

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

KEYBINDINGS_TEMPLATE = """# claude-code-py keybindings
# Add one mapping per line using key = action
# Example:
# ctrl+j = prompt:submit
# ctrl+k = transcript:focus
"""


def build_keybindings_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        path = _keybindings_path()
        file_exists = path.exists()
        if not file_exists:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(KEYBINDINGS_TEMPLATE, encoding="utf-8")
        text = path.read_text(encoding="utf-8")
        return CommandResult(
            kind="message",
            message=(
                f"{'Opened' if file_exists else 'Created'} {path}. "
                "Use the editor dialog to inspect or modify it."
            ),
            editor_kind="keybindings-editor",
            editor_title="Keybindings",
            editor_path=str(path),
            editor_text=text,
            editor_language="toml",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="keybindings",
            description="Open or create your keybindings configuration file.",
            command_type="local_ui",
        ),
        usage="/keybindings",
        handler=handler,
    )


def _keybindings_path() -> Path:
    return Path.home() / ".claude" / "keybindings"
