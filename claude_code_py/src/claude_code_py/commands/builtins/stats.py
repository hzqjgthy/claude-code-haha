from collections import Counter

from claude_code_py.commands.builtins._helpers import format_duration_ms
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_stats_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        sessions = context.session_service.list_sessions(limit=200)
        usages = context.runtime_state_store.list_session_usage()
        model_counts = Counter(
            usage.last_model for usage in usages if usage.last_model is not None
        )
        total_requests = sum(usage.request_count for usage in usages)
        total_cost = sum(usage.total_cost_usd for usage in usages)
        total_duration_ms = sum(usage.total_duration_ms for usage in usages)
        lines = [
            "Claude Code stats:",
            f"session_count: {len(sessions)}",
            f"usage_sessions: {len(usages)}",
            f"total_requests: {total_requests}",
            f"total_duration: {format_duration_ms(total_duration_ms)}",
            f"total_estimated_cost_usd: ${total_cost:.6f}",
        ]
        if model_counts:
            lines.append("models:")
            for model, count in model_counts.most_common(8):
                lines.append(f"- {model}: {count}")
        else:
            lines.append("models: (none)")
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:stats",
            dialog_title="Stats",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="stats",
            description="Show Claude Code usage statistics and activity.",
            command_type="local_ui",
        ),
        usage="/stats",
        handler=handler,
    )
