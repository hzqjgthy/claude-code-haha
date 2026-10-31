from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_insights_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        sessions = context.session_service.list_sessions(limit=20)
        usages = context.runtime_state_store.list_session_usage()[:20]
        prompt_lines = [
            "Generate a report analyzing Claude Code session patterns.",
            "",
            "Recent sessions:",
        ]
        if sessions:
            prompt_lines.extend(
                f"- {session.session_id}: {session.title} ({session.message_count} messages)"
                for session in sessions
            )
        else:
            prompt_lines.append("- none")
        prompt_lines.extend(["", "Recent usage snapshots:"])
        if usages:
            prompt_lines.extend(
                (
                    f"- {usage.session_id}: {usage.request_count} requests, "
                    f"${usage.total_cost_usd:.6f}, model={usage.last_model or '(unknown)'}"
                )
                for usage in usages
            )
        else:
            prompt_lines.append("- none")
        prompt_lines.append("")
        prompt_lines.append(
            "Provide an at-a-glance summary, recurring patterns, friction points, and practical suggestions.",
        )
        return CommandResult(
            kind="prompt",
            prompt="\n".join(prompt_lines),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="insights",
            description="Generate a report analyzing your Claude Code sessions.",
            command_type="prompt",
        ),
        usage="/insights",
        handler=handler,
    )
