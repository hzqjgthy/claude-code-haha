from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

VALID_EFFORT_LEVELS = ("low", "medium", "high", "max")


def build_effort_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.strip().lower()
        prefs = context.runtime_state_store.get_preferences()

        if args in {"", "current", "status"}:
            current = prefs.effort_level or "auto"
            return CommandResult(
                kind="message",
                message=f"Current effort level: {current}",
            )

        if args in {"help", "-h", "--help"}:
            return CommandResult(
                kind="message",
                message=(
                    "Usage: /effort [low|medium|high|max|auto]\n"
                    "Use /effort status to inspect the current level."
                ),
            )

        if args in {"auto", "unset"}:
            context.runtime_state_store.update_preferences(effort_level=None)
            return CommandResult(
                kind="message",
                message="Effort level set to auto.",
            )

        if args not in VALID_EFFORT_LEVELS:
            return CommandResult(
                kind="error",
                message="Invalid effort level. Use low, medium, high, max, or auto.",
            )

        context.runtime_state_store.update_preferences(effort_level=args)
        return CommandResult(
            kind="message",
            message=f"Set effort level to {args}.",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="effort",
            description="Set effort level for model usage.",
            command_type="local_ui",
            argument_hint="[low|medium|high|max|auto]",
        ),
        usage="/effort [low|medium|high|max|auto]",
        handler=handler,
    )
