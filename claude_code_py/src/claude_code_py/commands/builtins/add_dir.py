from pathlib import Path

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_add_dir_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        raw_args = invocation.args.strip()
        if not raw_args or raw_args == "list":
            lines = _render_working_directory_lines(context)
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:add-dir",
                dialog_title="Working Directories",
                dialog_lines=lines,
            )

        candidate = Path(raw_args).expanduser()
        if not candidate.is_absolute():
            candidate = (context.tool_context.cwd / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not candidate.exists():
            return CommandResult(
                kind="error",
                message=f"Path not found: {candidate}",
            )
        if not candidate.is_dir():
            return CommandResult(
                kind="error",
                message=f"{candidate} is not a directory.",
            )

        for root in context.tool_context.allowed_roots():
            if candidate == root or candidate.is_relative_to(root):
                return CommandResult(
                    kind="message",
                    message=(
                        f"{candidate} is already accessible within working directory "
                        f"{root}."
                    ),
                )

        added = context.tool_context.register_additional_root(str(candidate))
        return CommandResult(
            kind="message",
            message=(
                f"Added {added} as a working directory for this session. "
                "Claude can now resolve files under this path."
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="add-dir",
            description="Add a new working directory.",
            command_type="local_ui",
            argument_hint="<path>",
        ),
        usage="/add-dir <path>",
        handler=handler,
    )


def _render_working_directory_lines(context: CommandContext) -> list[str]:
    roots = context.tool_context.allowed_roots()
    lines = ["Working directories:"]
    for index, root in enumerate(roots, start=1):
        label = "workspace" if index == 1 else "additional"
        lines.append(f"{index}. {root} ({label})")
    lines.append("Use /add-dir <path> to add another working directory.")
    return lines
