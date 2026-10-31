from claude_code_py.commands.builtins._helpers import format_duration_ms
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_cost_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        usage = context.runtime_state_store.get_session_usage(
            context.session_state.metadata.session_id,
        )
        if usage is None:
            lines = [
                "No tracked API usage for this session yet.",
                "Run at least one model request, then /cost will show duration and token totals.",
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:cost",
                dialog_title="Cost",
                dialog_lines=lines,
            )

        lines = [
            "Session usage:",
            f"session_id: {usage.session_id}",
            f"requests: {usage.request_count}",
            f"duration: {format_duration_ms(usage.total_duration_ms)}",
            f"input_tokens: {usage.input_tokens}",
            f"output_tokens: {usage.output_tokens}",
            f"cache_creation_input_tokens: {usage.cache_creation_input_tokens}",
            f"cache_read_input_tokens: {usage.cache_read_input_tokens}",
            f"last_model: {usage.last_model or '(unknown)'}",
        ]
        if usage.priced_request_count > 0:
            lines.append(f"estimated_cost_usd: ${usage.total_cost_usd:.6f}")
        else:
            lines.append("estimated_cost_usd: unavailable")
        if usage.unpriced_request_count > 0:
            lines.append(
                f"unpriced_requests: {usage.unpriced_request_count} "
                "(model pricing table unavailable)",
            )
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:cost",
            dialog_title="Cost",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="cost",
            description="Show tracked session duration, token usage, and estimated cost.",
            command_type="local_ui",
        ),
        usage="/cost",
        handler=handler,
    )
