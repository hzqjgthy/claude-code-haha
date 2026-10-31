from claude_code_py.application.file_history_service import FileHistoryService
from claude_code_py.commands.loader import (
    CommandDialogAction,
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_rewind_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        messages = context.session_state.messages
        history_service = FileHistoryService(
            context.container.paths.data_dir / "file_history"
        )
        rewind_points = [
            (
                index + 1,
                position,
                message.id,
                message.content,
            )
            for position, message in enumerate(messages)
            if message.kind == "user"
            for index in [sum(1 for item in messages[: position + 1] if item.kind == "user") - 1]
        ]
        if not rewind_points:
            return CommandResult(
                kind="message",
                message="No user turns available to rewind.",
            )

        raw_arg = invocation.args.strip().lower()
        if not raw_arg:
            lines = ["Rewind points:"]
            for turn_number, _, turn_id, content in rewind_points:
                snapshot = history_service.snapshot_for_turn(
                    context.session_state.metadata.session_id,
                    turn_id,
                )
                file_count = len(snapshot.files) if snapshot is not None else 0
                lines.append(
                    f"{turn_number} | files={file_count} | {_trim_preview(content)}"
                )
            lines.append("Use /rewind last or /rewind <turn_number>.")
            actions = [
                CommandDialogAction(
                    label=f"Turn {turn_number}",
                    command=f"/rewind {turn_number}",
                    description=_trim_preview(content, limit=40),
                )
                for turn_number, _, _, content in reversed(rewind_points[-8:])
            ]
            selector_options = []
            for turn_number, _, turn_id, content in reversed(rewind_points):
                snapshot = history_service.snapshot_for_turn(
                    context.session_state.metadata.session_id,
                    turn_id,
                )
                file_count = len(snapshot.files) if snapshot is not None else 0
                selector_options.append(
                    CommandSelectorOption(
                        label=f"Turn {turn_number}",
                        command=f"/rewind {turn_number}",
                        description=_trim_preview(content, limit=48),
                        preview_lines=[
                            f"user turn: {turn_number}",
                            f"prompt: {content.strip() or '(empty)'}",
                            f"file_snapshot_count: {file_count}",
                            "",
                            "Selecting this rewinds the session to just before this user turn.",
                        ],
                    )
                )
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_actions=actions,
                selector_kind="selector:rewind",
                selector_title="Select Rewind Point",
                selector_options=selector_options,
            )

        if raw_arg == "last":
            target_turn = rewind_points[-1][0]
        else:
            try:
                target_turn = int(raw_arg)
            except ValueError:
                return CommandResult(
                    kind="error",
                    message="Usage: /rewind, /rewind last, or /rewind <turn_number>",
                )

        target = next(
            (point for point in rewind_points if point[0] == target_turn),
            None,
        )
        if target is None:
            return CommandResult(
                kind="error",
                message=f"Unknown rewind turn '{raw_arg}'.",
            )

        _, message_index, turn_id, prompt = target
        updated_messages = messages[:message_index]
        restore_report = history_service.restore_turn(
            session_id=context.session_state.metadata.session_id,
            turn_id=turn_id,
            allowed_roots=context.tool_context.allowed_roots(),
        )
        context.session_state = context.session_service.rewrite_messages(
            context.session_state,
            updated_messages,
        )
        pruned = history_service.prune_to_turn_ids(
            context.session_state.metadata.session_id,
            {
                message.id
                for message in context.session_state.messages
                if message.kind == "user"
            },
        )
        context.bind_status()
        restore_suffix = ""
        if restore_report is not None:
            restore_suffix = (
                " | "
                f"files restored={restore_report.restored_files}, "
                f"deleted={restore_report.deleted_files}, "
                f"snapshot_files={restore_report.snapshot_file_count}"
            )
        return CommandResult(
            kind="message",
            message=(
                f"Rewound session before turn {target_turn}: {_trim_preview(prompt)}"
                f"{restore_suffix} | pruned_snapshots={pruned}"
            ),
            refresh_transcript=True,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="rewind",
            description="List rewind points or rewind the current session to an earlier user turn.",
            command_type="local_ui",
            argument_hint="[last|turn_number]",
            aliases=["checkpoint"],
        ),
        usage="/rewind [last|turn_number]",
        handler=handler,
    )


def _trim_preview(value: str, *, limit: int = 72) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."
