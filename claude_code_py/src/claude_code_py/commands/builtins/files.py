from pathlib import Path

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.tools.file_context import FILE_CONTEXT_METADATA_KEY, list_file_context_paths


def build_files_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        action = invocation.args.strip().lower()
        if action == "clear":
            tracked = list_file_context_paths(context.tool_context)
            context.tool_context.metadata[FILE_CONTEXT_METADATA_KEY] = []
            return CommandResult(
                kind="message",
                message=f"Cleared {len(tracked)} tracked file(s) from context.",
            )

        tracked = list_file_context_paths(context.tool_context)
        if not tracked:
            return CommandResult(
                kind="message",
                message=(
                    "No files in context. Read/Edit/Write tool calls populate this list."
                ),
            )

        lines = [f"Files in context: {len(tracked)}"]
        for path in tracked:
            lines.append(_display_path(context.workspace_root, path))
        lines.append("Use /files clear to reset the tracked file context.")
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:files",
            dialog_title="Files In Context",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="files",
            description="List the files currently tracked in tool context.",
            command_type="local_ui",
            argument_hint="[clear]",
        ),
        usage="/files [clear]",
        handler=handler,
    )


def _display_path(workspace_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(workspace_root))
    except ValueError:
        return str(path)
