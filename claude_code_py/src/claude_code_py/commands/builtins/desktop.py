from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_desktop_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        transcript_path = (
            context.container.paths.sessions_dir
            / f"{context.session_state.metadata.session_id}.jsonl"
        )
        lines = [
            "Claude Desktop handoff:",
            f"session_id: {context.session_state.metadata.session_id}",
            f"title: {context.session_state.metadata.title}",
            f"transcript_path: {transcript_path}",
            "Direct Desktop handoff is not implemented yet in claude-code-py.",
            "Until the remote/desktop stage lands, use the session id and transcript path to continue manually.",
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:desktop",
            dialog_title="Desktop",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="desktop",
            description="Show the current session details for Desktop handoff.",
            command_type="local_ui",
            aliases=["app"],
        ),
        usage="/desktop",
        handler=handler,
    )
