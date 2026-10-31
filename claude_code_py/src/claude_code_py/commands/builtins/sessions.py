from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_sessions_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        del invocation
        sessions = context.session_service.list_sessions(limit=20)
        if not sessions:
            return CommandResult(kind="message", message="No saved sessions found.")

        tags = context.runtime_state_store.list_session_tags()
        backgrounded = context.runtime_state_store.list_backgrounded_sessions()
        current_id = context.session_state.metadata.session_id
        lines = ["Sessions:"]
        selector_options: list[CommandSelectorOption] = []
        for session in sessions:
            marker = "*" if session.session_id == current_id else " "
            bg = "yes" if backgrounded.get(session.session_id) else "no"
            tag = tags.get(session.session_id)
            line = (
                f"{marker} {session.session_id} | bg={bg} | "
                f"messages={session.message_count} | {session.title}"
            )
            if tag:
                line += f" | #{tag}"
            lines.append(line)
            selector_options.append(
                CommandSelectorOption(
                    label=f"{session.title} ({session.session_id[:8]})",
                    command=f"/resume {session.session_id}",
                    description=f"bg={bg} | messages={session.message_count}",
                    preview_lines=[
                        f"session_id: {session.session_id}",
                        f"title: {session.title}",
                        f"updated_at: {session.updated_at.isoformat(timespec='seconds')}",
                        f"backgrounded: {bg}",
                        f"message_count: {session.message_count}",
                        f"transcript_path: {session.transcript_path}",
                    ],
                )
            )
        lines.append("Use /resume <session_id> to switch sessions.")
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            selector_kind="selector:sessions",
            selector_title="Select Session",
            selector_options=selector_options,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="sessions",
            description="List recent sessions for concurrent local work.",
            command_type="local_ui",
            aliases=["history"],
        ),
        usage="/sessions",
        handler=handler,
    )
