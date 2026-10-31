from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

AGENT_COLORS = (
    "red",
    "blue",
    "green",
    "yellow",
    "purple",
    "orange",
    "pink",
    "cyan",
)
RESET_ALIASES = {"default", "reset", "none", "gray", "grey"}


def build_color_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.strip().lower()
        session_id = context.session_state.metadata.session_id
        current = context.runtime_state_store.get_session_color(session_id)

        if not args:
            lines = [
                "Session color:",
                f"current: {current or 'default'}",
                f"available: {', '.join(AGENT_COLORS)}, default",
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:color",
                dialog_title="Color",
                dialog_lines=lines,
            )

        if args in RESET_ALIASES:
            context.runtime_state_store.set_session_color(session_id, None)
            return CommandResult(
                kind="message",
                message="Session color reset to default.",
            )

        if args not in AGENT_COLORS:
            return CommandResult(
                kind="error",
                message=(
                    f'Invalid color "{args}". '
                    f"Available colors: {', '.join(AGENT_COLORS)}, default"
                ),
            )

        context.runtime_state_store.set_session_color(session_id, args)
        return CommandResult(
            kind="message",
            message=f"Session color set to: {args}",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="color",
            description="Set the prompt bar color for this session.",
            command_type="local_ui",
            argument_hint="<color|default>",
        ),
        usage="/color <red|blue|green|yellow|purple|orange|pink|cyan|default>",
        handler=handler,
    )
