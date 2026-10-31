from datetime import datetime
from pathlib import Path

from claude_code_py.commands.builtins._session_exports import (
    infer_export_format,
    render_export_content,
)
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_export_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        messages = context.session_state.messages
        if not messages:
            return CommandResult(
                kind="error",
                message="No conversation to export.",
            )

        export_path = _resolve_export_path(context, invocation.args.strip(), messages)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        fmt = infer_export_format(export_path)
        content = render_export_content(context, fmt=fmt)
        export_path.write_text(content, encoding="utf-8")
        return CommandResult(
            kind="message",
            message=f"Conversation exported to: {export_path}",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="export",
            description="Export the current conversation to text, markdown, or JSON.",
            command_type="local_ui",
            argument_hint="[filename(.txt|.md|.json)]",
        ),
        usage="/export [filename(.txt|.md|.json)]",
        handler=handler,
    )


def _resolve_export_path(
    context: CommandContext,
    raw_filename: str,
    messages,
) -> Path:
    if raw_filename:
        candidate = Path(raw_filename).expanduser()
        if not candidate.is_absolute():
            candidate = context.tool_context.cwd / candidate
        if candidate.suffix.lower() not in {".txt", ".md", ".json"}:
            candidate = candidate.with_suffix(".txt")
        return candidate.resolve()

    first_prompt = _extract_first_prompt(messages)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    suffix = _sanitize_filename(first_prompt) if first_prompt else "conversation"
    return (context.tool_context.cwd / f"{timestamp}-{suffix}.txt").resolve()


def _extract_first_prompt(messages) -> str:
    for message in messages:
        if message.kind != "user":
            continue
        first_line = message.content.strip().splitlines()[0] if message.content else ""
        return first_line[:50].strip()
    return ""


def _sanitize_filename(text: str) -> str:
    lowered = text.lower()
    allowed = [
        char
        for char in lowered
        if char.isalnum() or char in {" ", "-"}
    ]
    collapsed = "".join(allowed).strip()
    return "-".join(collapsed.split()) or "conversation"
