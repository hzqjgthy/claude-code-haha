from claude_code_py.commands.loader import CommandContext, CommandResult, SlashCommand, SlashCommandInvocation
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.session.recovery import RecoveryRequest


def build_clear_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        recovery = context.session_service.recover(RecoveryRequest())
        previous_session_id = context.session_state.metadata.session_id
        context.session_state = recovery.state
        context.bind_status()
        return CommandResult(
            kind="message",
            message=(
                f"Started a new session {context.session_state.metadata.session_id} "
                f"(previous session was {previous_session_id})."
            ),
            refresh_transcript=True,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="clear",
            description="Start a fresh session without previous history.",
            command_type="local",
            aliases=["reset", "new"],
        ),
        usage="/clear",
        handler=handler,
    )
