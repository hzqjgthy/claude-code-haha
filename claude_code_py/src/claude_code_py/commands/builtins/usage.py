from claude_code_py.commands.builtins._helpers import format_duration_ms
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_usage_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        usages = context.runtime_state_store.list_session_usage()
        if not usages:
            return CommandResult(
                kind="message",
                message="No usage has been recorded yet.",
            )
        total_requests = sum(item.request_count for item in usages)
        total_cost = sum(item.total_cost_usd for item in usages)
        total_duration_ms = sum(item.total_duration_ms for item in usages)
        lines = [
            "Usage:",
            f"tracked_sessions: {len(usages)}",
            f"total_requests: {total_requests}",
            f"total_duration: {format_duration_ms(total_duration_ms)}",
            f"total_estimated_cost_usd: ${total_cost:.6f}",
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:usage",
            dialog_title="Usage",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="usage",
            description="Show plan usage limits and tracked request totals.",
            command_type="local_ui",
        ),
        usage="/usage",
        handler=handler,
    )
