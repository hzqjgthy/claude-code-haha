from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.domain.messages import UserMessage
from claude_code_py.domain.sessions import SessionMetadata, SessionState


def build_branch_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        current = context.session_state
        title = _derive_branch_title(current, invocation.args.strip())
        metadata = SessionMetadata(
            parent_session_id=current.metadata.session_id,
            title=title,
        )
        branched_state = SessionState(
            metadata=metadata,
            messages=list(current.messages),
        )
        if branched_state.messages:
            branched_state = context.session_service.rewrite_messages(
                branched_state,
                branched_state.messages,
            )
        context.session_state = branched_state
        context.bind_status()
        context.tool_context.metadata["session_id"] = branched_state.metadata.session_id
        return CommandResult(
            kind="message",
            message=(
                f"Created branched session {branched_state.metadata.session_id} "
                f"from {current.metadata.session_id}."
            ),
            refresh_transcript=True,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="branch",
            description="Create a branch of the current conversation at this point.",
            command_type="local_ui",
            argument_hint="[name]",
            aliases=["fork"],
        ),
        usage="/branch [name]",
        handler=handler,
    )


def _derive_branch_title(state: SessionState, raw_title: str) -> str:
    normalized = " ".join(raw_title.split())
    if normalized:
        return normalized
    first_user = next(
        (message for message in state.messages if isinstance(message, UserMessage)),
        None,
    )
    if first_user is not None and first_user.content.strip():
        return " ".join(first_user.content.split())[:100]
    return "Branched conversation"
