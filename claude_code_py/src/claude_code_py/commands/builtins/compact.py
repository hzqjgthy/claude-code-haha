from collections import Counter

from claude_code_py.application.file_history_service import FileHistoryService
from claude_code_py.application.session_memory_service import SessionMemoryService
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.domain.messages import AssistantMessage, Message, UserMessage


def build_compact_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        messages = list(context.session_state.messages)
        if not messages:
            return CommandResult(
                kind="error",
                message="No messages to compact.",
            )

        raw_args = invocation.args.strip()
        mode, instructions = _parse_mode_and_instructions(raw_args)
        if mode == "micro":
            rewritten_messages, summary = _build_micro_compaction(messages, instructions)
            compact_label = "Conversation micro-compacted."
        else:
            summary = _build_compact_summary(messages, instructions)
            rewritten_messages = [
                UserMessage(content=f"Conversation summary:\n{summary}"),
                AssistantMessage(
                    content="Acknowledged. I will use this compacted summary as prior context.",
                ),
            ]
            compact_label = "Conversation compacted."

        context.session_state = context.session_service.rewrite_messages(
            context.session_state,
            rewritten_messages,
        )
        memory_path, _ = SessionMemoryService(
            context.container.paths.data_dir / "session_memory"
        ).update_from_session(
            context.session_state,
            workspace_root=context.workspace_root,
            tool_context=context.tool_context,
            model_name=context.model_name,
            instructions=instructions,
        )
        removed_snapshots = FileHistoryService(
            context.container.paths.data_dir / "file_history"
        ).prune_to_turn_ids(
            context.session_state.metadata.session_id,
            {
                message.id
                for message in context.session_state.messages
                if message.kind == "user"
            },
        )
        context.bind_status()
        lines = [
            compact_label,
            f"mode: {mode}",
            f"session_memory: {memory_path}",
            f"removed_file_history_snapshots: {removed_snapshots}",
            "",
            summary,
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            refresh_transcript=True,
            dialog_kind="command:compact",
            dialog_title="Compact",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="compact",
            description=(
                "Compact conversation history with full or micro compaction."
            ),
            command_type="local_ui",
            argument_hint="[micro] <optional summarization instructions>",
        ),
        usage="/compact [micro] [optional custom summarization instructions]",
        handler=handler,
    )


def _parse_mode_and_instructions(raw_args: str) -> tuple[str, str]:
    stripped = raw_args.strip()
    if not stripped:
        return "full", ""
    parts = stripped.split(maxsplit=1)
    if parts[0].lower() == "micro":
        return "micro", parts[1].strip() if len(parts) > 1 else ""
    return "full", stripped


def _build_micro_compaction(
    messages: list[Message],
    instructions: str,
) -> tuple[list[Message], str]:
    keep_start = _find_micro_keep_start(messages, keep_user_turns=2)
    if keep_start <= 0:
        summary = _build_compact_summary(messages, instructions)
        return (
            [
                UserMessage(content=f"Conversation summary:\n{summary}"),
                AssistantMessage(
                    content="Acknowledged. I will use this compacted summary as prior context.",
                ),
            ],
            summary,
        )

    compacted_segment = messages[:keep_start]
    kept_segment = messages[keep_start:]
    summary = _build_compact_summary(
        compacted_segment,
        instructions or "Micro compact preserved the most recent user turns.",
    )
    rewritten = [
        UserMessage(content=f"Conversation summary:\n{summary}"),
        AssistantMessage(
            content="Acknowledged. I will use the summary plus the preserved recent turns.",
        ),
        *kept_segment,
    ]
    return rewritten, summary


def _find_micro_keep_start(messages: list[Message], *, keep_user_turns: int) -> int:
    user_seen = 0
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].kind == "user":
            user_seen += 1
            if user_seen == keep_user_turns:
                return index
    return 0


def _build_compact_summary(messages: list[Message], instructions: str) -> str:
    lines = [
        "Compacted conversation summary",
        f"message_count: {len(messages)}",
    ]
    if instructions:
        lines.append(f"custom_instructions: {instructions}")

    user_messages = [
        message.content.strip()
        for message in messages
        if isinstance(message, UserMessage) and message.content.strip()
    ]
    assistant_messages = [
        message.content.strip()
        for message in messages
        if isinstance(message, AssistantMessage) and message.content.strip()
    ]
    tool_counts = Counter(
        message.tool_name
        for message in messages
        if getattr(message, "kind", None) == "tool_use"
    )

    if user_messages:
        lines.append("recent_user_goals:")
        for value in user_messages[-5:]:
            lines.append(f"- {_truncate(value, limit=160)}")
    if assistant_messages:
        lines.append("recent_assistant_state:")
        for value in assistant_messages[-4:]:
            lines.append(f"- {_truncate(value, limit=160)}")
    if tool_counts:
        lines.append("tool_activity:")
        for name, count in tool_counts.most_common(8):
            lines.append(f"- {name}: {count}")
    return "\n".join(lines)


def _truncate(value: str, *, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."
