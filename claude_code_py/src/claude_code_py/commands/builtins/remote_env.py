from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_remote_env_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.strip()
        prefs = context.runtime_state_store.get_preferences()
        if not args or args == "show":
            lines = [
                "Remote environment:",
                (
                    "default_remote_environment: "
                    f"{prefs.default_remote_environment or '(none)'}"
                ),
                (
                    "remote_mode: "
                    f"{context.remote_provider.status().mode if context.remote_provider else 'local'}"
                ),
                "Use /remote-env set <name> or /remote-env clear.",
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:remote-env",
                dialog_title="Remote Environment",
                dialog_lines=lines,
            )
        if args == "clear":
            context.runtime_state_store.update_preferences(
                default_remote_environment=None,
            )
            return CommandResult(
                kind="message",
                message="Cleared the default remote environment preference.",
            )
        if args.startswith("set "):
            value = args[4:].strip()
            if not value:
                return CommandResult(
                    kind="error",
                    message="Usage: /remote-env set <environment-name>",
                )
            context.runtime_state_store.update_preferences(
                default_remote_environment=value,
            )
            return CommandResult(
                kind="message",
                message=f"Default remote environment set to {value}.",
            )
        return CommandResult(
            kind="error",
            message="Usage: /remote-env [show|set <environment-name>|clear]",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="remote-env",
            description="Show or change the default remote environment preference.",
            command_type="local_ui",
            argument_hint="[show|set <environment-name>|clear]",
        ),
        usage="/remote-env [show|set <environment-name>|clear]",
        handler=handler,
    )
