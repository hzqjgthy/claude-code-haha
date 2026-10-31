import json

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.tools.file_context import list_file_context_paths


def build_context_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        full_view = invocation.args.strip().lower() == "full"
        history = context.session_service.get_history(
            context.session_state.metadata.session_id
        )
        messages = history.messages

        user_count = sum(1 for message in messages if message.kind == "user")
        assistant_count = sum(
            1 for message in messages if message.kind == "assistant"
        )
        tool_count = sum(1 for message in messages if message.kind.startswith("tool_"))
        file_context = list_file_context_paths(context.tool_context)

        lines = [
            "Context snapshot:",
            "view: raw session history "
            "(compact/context-collapse parity is not implemented yet)",
            f"session_id: {history.summary.session_id}",
            f"title: {history.summary.title}",
            f"message_count: {len(messages)}",
            f"user_messages: {user_count}",
            f"assistant_messages: {assistant_count}",
            f"tool_messages: {tool_count}",
            f"system_prompt_configured: {'yes' if context.base_system_prompt else 'no'}",
            f"files_in_context: {len(file_context)}",
            f"plugin_count: {len(context.plugins)}",
            f"mcp_tool_count: {len(context.mcp_tool_definitions)}",
            f"first_user_message: {history.summary.first_user_message or '(none)'}",
            f"last_user_message: {history.summary.last_user_message or '(none)'}",
            "last_assistant_message: "
            f"{history.summary.last_assistant_message or '(none)'}",
        ]

        selected = messages if full_view else messages[-6:]
        if selected:
            lines.extend(
                [
                    "",
                    "messages:",
                ]
            )
            for message in selected:
                lines.append(_render_message_preview(message))
        else:
            lines.extend(["", "messages: (none)"])

        if not full_view and len(messages) > len(selected):
            lines.append("")
            lines.append("Use /context full to inspect the complete message list.")

        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:context",
            dialog_title="Context",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="context",
            description="Inspect the current conversation context snapshot.",
            command_type="local_ui",
            argument_hint="[full]",
        ),
        usage="/context [full]",
        handler=handler,
    )


def _render_message_preview(message) -> str:
    if message.kind in {"user", "assistant"}:
        return f"{message.kind}: {_trim_preview(message.content)}"
    if message.kind == "tool_use":
        arguments = json.dumps(
            message.arguments,
            ensure_ascii=False,
            sort_keys=True,
        )
        return f"tool_use:{message.tool_name} {_trim_preview(arguments)}"
    if message.kind == "tool_result":
        prefix = "tool_error" if message.is_error else "tool_result"
        return f"{prefix}:{message.tool_name} {_trim_preview(message.output)}"
    return f"{message.kind}: (unsupported preview)"


def _trim_preview(value: str, *, limit: int = 120) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."
