from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_think_back_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        sessions = context.session_service.list_sessions(limit=50)
        usages = context.runtime_state_store.list_session_usage()[:50]
        lines = [
            "Create a 'Claude Code Year in Review' style retrospective from these sessions.",
            "",
            f"session_count: {len(sessions)}",
            f"usage_snapshots: {len(usages)}",
        ]
        for session in sessions[:20]:
            lines.append(
                f"- {session.updated_at.date()}: {session.title} ({session.message_count} messages)"
            )
        return CommandResult(kind="prompt", prompt="\n".join(lines))

    return SlashCommand(
        spec=CommandSpec(
            name="think-back",
            description="Your Claude Code Year in Review.",
            command_type="prompt",
        ),
        usage="/think-back",
        handler=handler,
    )
