from __future__ import annotations

import json
from pathlib import Path

from claude_code_py.domain.messages import Message, deserialize_message


class HydratedRemoteBundle:
    def __init__(
        self,
        *,
        remote_session_id: str | None,
        title: str | None,
        session_url: str | None,
        messages: list[Message],
        source_path: Path,
    ) -> None:
        self.remote_session_id = remote_session_id
        self.title = title
        self.session_url = session_url
        self.messages = messages
        self.source_path = source_path


def load_hydrated_remote_bundle(path: Path) -> HydratedRemoteBundle:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid remote bundle: {path}")
    session = raw.get("session")
    if not isinstance(session, dict):
        raise ValueError(f"Remote bundle is missing session metadata: {path}")
    raw_messages = raw.get("messages")
    if not isinstance(raw_messages, list):
        raise ValueError(f"Remote bundle is missing messages: {path}")
    messages: list[Message] = []
    for item in raw_messages:
        if not isinstance(item, dict):
            continue
        messages.append(deserialize_message(item))
    return HydratedRemoteBundle(
        remote_session_id=session.get("session_id")
        if isinstance(session.get("session_id"), str)
        else None,
        title=session.get("title") if isinstance(session.get("title"), str) else None,
        session_url=session.get("session_url")
        if isinstance(session.get("session_url"), str)
        else None,
        messages=messages,
        source_path=path.resolve(),
    )
