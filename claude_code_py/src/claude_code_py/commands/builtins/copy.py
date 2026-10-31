from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.common.clipboard import ClipboardError, copy_text_to_clipboard
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.domain.messages import AssistantMessage


def build_copy_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        index = _parse_index(invocation.args.strip())
        if index is None:
            return CommandResult(
                kind="error",
                message="Usage: /copy [N] where N is the Nth-latest assistant response.",
            )
        candidates = [
            message.content
            for message in reversed(context.session_state.messages)
            if isinstance(message, AssistantMessage) and message.content.strip()
        ]
        if not candidates:
            return CommandResult(
                kind="error",
                message="No assistant response is available to copy yet.",
            )
        if index >= len(candidates):
            return CommandResult(
                kind="error",
                message=f"Only {len(candidates)} assistant responses are available to copy.",
            )
        target = candidates[index]
        try:
            backend = copy_text_to_clipboard(target)
        except ClipboardError as exc:
            return CommandResult(kind="error", message=str(exc))
        char_count = len(target)
        line_count = target.count("\n") + 1
        return CommandResult(
            kind="message",
            message=(
                f"Copied assistant response #{index + 1} via {backend} "
                f"({char_count} characters, {line_count} lines)."
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="copy",
            description="Copy Claude's last response to the clipboard.",
            command_type="local_ui",
            argument_hint="[N]",
        ),
        usage="/copy [N]",
        handler=handler,
    )


def _parse_index(value: str) -> int | None:
    if not value:
        return 0
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed - 1
