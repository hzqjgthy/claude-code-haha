from __future__ import annotations

from collections import Counter
from pathlib import Path

from claude_code_py.domain.messages import AssistantMessage, Message, UserMessage
from claude_code_py.domain.sessions import SessionState
from claude_code_py.tools.file_context import list_file_context_paths
from claude_code_py.tools.permission_preview import clip_text


class SessionMemoryService:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def memory_path(self, session_id: str) -> Path:
        return self._base_dir / f"{session_id}.md"

    def load(self, session_id: str) -> str | None:
        path = self.memory_path(session_id)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def write(self, session_id: str, content: str) -> Path:
        path = self.memory_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        return path

    def update_from_session(
        self,
        state: SessionState,
        *,
        workspace_root: Path,
        tool_context,
        model_name: str,
        instructions: str = "",
    ) -> tuple[Path, str]:
        content = self.extract_from_session(
            state,
            workspace_root=workspace_root,
            tool_context=tool_context,
            model_name=model_name,
            instructions=instructions,
        )
        path = self.write(state.metadata.session_id, content)
        return path, content

    def extract_from_session(
        self,
        state: SessionState,
        *,
        workspace_root: Path,
        tool_context,
        model_name: str,
        instructions: str = "",
    ) -> str:
        messages = list(state.messages)
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
        file_paths = list_file_context_paths(tool_context)

        lines = [
            "# Session Memory",
            "",
            f"- session_id: {state.metadata.session_id}",
            f"- title: {state.metadata.title}",
            f"- model: {model_name}",
            f"- workspace: {workspace_root}",
            f"- message_count: {len(messages)}",
        ]
        if instructions:
            lines.extend(["", "## Extraction Notes", instructions])
        if user_messages:
            lines.extend(["", "## Current Goals"])
            for value in user_messages[-6:]:
                lines.append(f"- {clip_text(' '.join(value.split()), max_lines=1, max_chars=220)}")
        if assistant_messages:
            lines.extend(["", "## Working State"])
            for value in assistant_messages[-4:]:
                lines.append(f"- {clip_text(' '.join(value.split()), max_lines=1, max_chars=220)}")
        if tool_counts:
            lines.extend(["", "## Tool Activity"])
            for name, count in tool_counts.most_common(10):
                lines.append(f"- {name}: {count}")
        if file_paths:
            lines.extend(["", "## Files In Context"])
            for path in file_paths[-12:]:
                try:
                    rendered = str(path.relative_to(workspace_root))
                except ValueError:
                    rendered = str(path)
                lines.append(f"- {rendered}")
        lines.extend(
            [
                "",
                "## Latest Assistant Reply",
                assistant_messages[-1] if assistant_messages else "(none)",
            ]
        )
        return "\n".join(lines).strip()
