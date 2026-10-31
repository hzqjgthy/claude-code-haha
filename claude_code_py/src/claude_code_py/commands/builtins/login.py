from claude_code_py.commands.builtins._auth import auth_status_lines, set_api_key, set_auth_token
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_login_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.strip()
        if not args or args == "status":
            lines = [
                *auth_status_lines(context),
                "",
                "Usage:",
                "/login api-key <key>",
                "/login auth-token <token>",
                "",
                "The credential is written to the project's .env file and applied to the current provider immediately.",
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:login",
                dialog_title="Login",
                dialog_lines=lines,
            )
        if args.startswith("api-key "):
            value = args[len("api-key ") :].strip()
            if not value:
                return CommandResult(kind="error", message="Usage: /login api-key <key>")
            set_api_key(context, value)
            return CommandResult(
                kind="message",
                message="Configured ANTHROPIC_API_KEY and cleared ANTHROPIC_AUTH_TOKEN.",
            )
        if args.startswith("auth-token "):
            value = args[len("auth-token ") :].strip()
            if not value:
                return CommandResult(
                    kind="error",
                    message="Usage: /login auth-token <token>",
                )
            set_auth_token(context, value)
            return CommandResult(
                kind="message",
                message="Configured ANTHROPIC_AUTH_TOKEN and cleared ANTHROPIC_API_KEY.",
            )
        return CommandResult(
            kind="error",
            message="Usage: /login [status|api-key <key>|auth-token <token>]",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="login",
            description="Configure Anthropic credentials for the current project.",
            command_type="local_ui",
            argument_hint="[status|api-key <key>|auth-token <token>]",
        ),
        usage="/login [status|api-key <key>|auth-token <token>]",
        handler=handler,
    )
