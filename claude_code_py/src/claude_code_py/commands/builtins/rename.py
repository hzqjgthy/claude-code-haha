from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_rename_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        requested_title = " ".join(invocation.args.split())
        if not requested_title:
            return CommandResult(
                kind="message",
                message=f"Current session title: {context.session_state.metadata.title}",
            )

        try:
            context.session_state = context.session_service.rename_session(
                context.session_state,
                requested_title,
            )
        except ValueError as exc:
            return CommandResult(kind="error", message=str(exc))
        return CommandResult(
            kind="message",
            message=(
                f"Renamed session {context.session_state.metadata.session_id} "
                f"to '{context.session_state.metadata.title}'."
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="rename",
            description="Show or rename the current session title.",
            command_type="local_ui",
            argument_hint="[new title]",
        ),
        usage="/rename [new title]",
        handler=handler,
    )
