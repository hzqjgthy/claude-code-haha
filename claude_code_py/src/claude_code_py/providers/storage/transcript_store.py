from pathlib import Path

from claude_code_py.common.json import from_json, to_json
from claude_code_py.common.paths import ProjectPaths
from claude_code_py.domain.messages import Message, deserialize_message, serialize_message


class JsonlTranscriptStore:
    def __init__(self, paths: ProjectPaths) -> None:
        self._paths = paths
        self._paths.sessions_dir.mkdir(parents=True, exist_ok=True)

    def transcript_path(self, session_id: str) -> Path:
        return self._paths.sessions_dir / f"{session_id}.jsonl"

    def list_session_ids(self) -> list[str]:
        if not self._paths.sessions_dir.exists():
            return []
        return sorted(
            path.stem
            for path in self._paths.sessions_dir.glob("*.jsonl")
            if path.is_file()
        )

    def exists(self, session_id: str) -> bool:
        return self.transcript_path(session_id).exists()

    def load_messages(self, session_id: str) -> list[Message]:
        path = self.transcript_path(session_id)
        if not path.exists():
            return []

        messages: list[Message] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            payload = from_json(stripped)
            if not isinstance(payload, dict):
                continue
            messages.append(deserialize_message(payload))
        return messages

    def append_messages(self, session_id: str, messages: list[Message]) -> None:
        if not messages:
            return
        path = self.transcript_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for message in messages:
                handle.write(to_json(serialize_message(message)))
                handle.write("\n")

    def overwrite_messages(self, session_id: str, messages: list[Message]) -> None:
        path = self.transcript_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for message in messages:
                handle.write(to_json(serialize_message(message)))
                handle.write("\n")
