from claude_code_py.commands.loader import CommandContext, CommandResult, SlashCommand, SlashCommandInvocation
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.session.recovery import RecoveryRequest


def build_resume_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.split()
        if not args:
            sessions = context.session_service.list_sessions(limit=10)
            if not sessions:
                return CommandResult(kind="message", message="No saved sessions found.")
            tags = context.runtime_state_store.list_session_tags()
            backgrounded = context.runtime_state_store.list_backgrounded_sessions()
            lines = ["Recent sessions:"]
            for session in sessions:
                tag = tags.get(session.session_id)
                bg = "yes" if backgrounded.get(session.session_id) else "no"
                lines.append(
                    (
                        f"{session.session_id} | "
                        f"bg={bg} | "
                        f"{session.updated_at.isoformat(timespec='seconds')} | "
                        f"{session.title}"
                        + (f" | #{tag}" if tag else "")
                    ),
                )
            lines.append("Use /resume <session_id> or /resume <session_id> --fork")
            return CommandResult(kind="message", message="\n".join(lines))

        fork_session = False
        filtered_args: list[str] = []
        for token in args:
            if token == "--fork":
                fork_session = True
            else:
                filtered_args.append(token)
        target = filtered_args[0] if filtered_args else "latest"

        request = (
            RecoveryRequest(continue_latest=True, fork_session=fork_session)
            if target == "latest"
            else RecoveryRequest(
                resume_session_id=target,
                fork_session=fork_session,
            )
        )
        recovery = context.session_service.recover(request)
        context.session_state = recovery.state
        context.bind_status()
        action = "Forked from" if fork_session else "Resumed"
        source_session = (
            recovery.source_summary.session_id
            if recovery.source_summary is not None
            else target
        )
        return CommandResult(
            kind="message",
            message=(
                f"{action} session {source_session}. "
                f"Current session is {context.session_state.metadata.session_id}."
            ),
            refresh_transcript=True,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="resume",
            description="Resume a session or list recent sessions.",
            command_type="local_ui",
            argument_hint="[session_id|latest] [--fork]",
            aliases=["continue"],
        ),
        usage="/resume [session_id|latest] [--fork]",
        handler=handler,
    )
