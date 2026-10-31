from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Literal

from claude_code_py.application.file_history_service import FileHistoryService
from claude_code_py.application.session_memory_service import SessionMemoryService
from claude_code_py.domain.messages import serialize_message

ExportFormat = Literal["text", "markdown", "json"]


def infer_export_format(path: Path) -> ExportFormat:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "markdown"
    if suffix == ".json":
        return "json"
    return "text"


def render_export_content(context, *, fmt: ExportFormat) -> str:
    if fmt == "json":
        return json.dumps(
            build_share_bundle(context),
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    if fmt == "markdown":
        return _render_markdown(context)
    return _render_text(context)


def build_share_bundle(context) -> dict[str, object]:
    metadata = context.session_state.metadata
    memory_service = SessionMemoryService(
        context.container.paths.data_dir / "session_memory"
    )
    file_history_service = FileHistoryService(
        context.container.paths.data_dir / "file_history"
    )
    session_memory = memory_service.load(metadata.session_id)
    latest_snapshot = file_history_service.latest_snapshot(metadata.session_id)
    return {
        "bundle_format": "claude-code-py-share-bundle",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "session": {
            "session_id": metadata.session_id,
            "title": metadata.title,
            "parent_session_id": metadata.parent_session_id,
            "model": context.model_name,
            "permission_mode": context.permission_mode,
            "tag": context.runtime_state_store.get_session_tag(metadata.session_id),
            "backgrounded": context.runtime_state_store.is_session_backgrounded(
                metadata.session_id
            ),
        },
        "session_memory": session_memory,
        "file_history": {
            "snapshot_count": file_history_service.snapshot_count(metadata.session_id),
            "latest_turn_id": latest_snapshot.turn_id if latest_snapshot else None,
            "latest_snapshot_file_count": (
                len(latest_snapshot.files) if latest_snapshot is not None else 0
            ),
        },
        "messages": [
            serialize_message(message)
            for message in context.session_state.messages
        ],
    }


def _render_text(context) -> str:
    metadata = context.session_state.metadata
    lines = [
        f"Session ID: {metadata.session_id}",
        f"Title: {metadata.title}",
        f"Model: {context.model_name}",
        f"Permission Mode: {context.permission_mode}",
        f"Exported At: {datetime.now().isoformat(timespec='seconds')}",
        "",
    ]
    for message in context.session_state.messages:
        lines.extend(_render_message_text(message))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_markdown(context) -> str:
    metadata = context.session_state.metadata
    lines = [
        "# Session Export",
        "",
        f"- Session ID: `{metadata.session_id}`",
        f"- Title: {metadata.title}",
        f"- Model: `{context.model_name}`",
        f"- Permission Mode: `{context.permission_mode}`",
        f"- Exported At: {datetime.now().isoformat(timespec='seconds')}",
        "",
    ]
    for message in context.session_state.messages:
        lines.extend(_render_message_markdown(message))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_message_text(message) -> list[str]:
    if message.kind == "user":
        return ["User:", message.content]
    if message.kind == "assistant":
        return ["Claude:", message.content]
    if message.kind == "tool_use":
        arguments = json.dumps(message.arguments, ensure_ascii=False, indent=2)
        return [f"Tool Call: {message.tool_name}", arguments]
    if message.kind == "tool_result":
        label = "Tool Error" if message.is_error else "Tool Result"
        return [f"{label}: {message.tool_name}", message.output]
    return [f"{message.kind}:", "(unsupported export message)"]


def _render_message_markdown(message) -> list[str]:
    if message.kind == "user":
        return ["## User", "", message.content]
    if message.kind == "assistant":
        return ["## Claude", "", message.content]
    if message.kind == "tool_use":
        arguments = json.dumps(message.arguments, ensure_ascii=False, indent=2)
        return [
            f"## Tool Call: {message.tool_name}",
            "",
            "```json",
            arguments,
            "```",
        ]
    if message.kind == "tool_result":
        label = "Tool Error" if message.is_error else "Tool Result"
        return [
            f"## {label}: {message.tool_name}",
            "",
            "```text",
            message.output,
            "```",
        ]
    return [f"## {message.kind}", "", "(unsupported export message)"]
