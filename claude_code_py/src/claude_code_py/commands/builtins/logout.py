from claude_code_py.commands.builtins._auth import auth_status_lines, clear_auth
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_logout_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.strip()
        if args in {"", "confirm"}:
            clear_auth(context)
            return CommandResult(
                kind="message",
                message="Cleared ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN from the project .env file.",
            )
        if args == "status":
            lines = auth_status_lines(context)
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:logout",
                dialog_title="Logout",
                dialog_lines=lines,
            )
        return CommandResult(
            kind="error",
            message="Usage: /logout [status|confirm]",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="logout",
            description="Clear Anthropic credentials from the current project.",
            command_type="local_ui",
            argument_hint="[status|confirm]",
        ),
        usage="/logout [status|confirm]",
        handler=handler,
    )
