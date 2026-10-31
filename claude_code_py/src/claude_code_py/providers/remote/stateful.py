from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from claude_code_py.common.json import from_json, to_json
from claude_code_py.providers.remote.base import (
    ArchivedRemoteSession,
    RemoteProvider,
    RemoteTransport,
    RemoteStatus,
)


def _now_utc() -> datetime:
    return datetime.now(UTC)


class RemoteStateDocument(BaseModel):
    current: RemoteStatus = Field(default_factory=RemoteStatus)
    archived: list[ArchivedRemoteSession] = Field(default_factory=list)


class StatefulRemoteProvider(RemoteProvider):
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def status(self) -> RemoteStatus:
        return self._load().current.model_copy(deep=True)

    def connect_direct(
        self,
        *,
        session_url: str,
        local_session_id: str,
        remote_session_id: str | None = None,
        transport: RemoteTransport = "websocket",
        detail: str | None = None,
    ) -> RemoteStatus:
        return self._set_current(
            RemoteStatus(
                mode="direct_connect",
                connected=True,
                session_url=session_url,
                detail=detail or "Direct connect session",
                remote_session_id=remote_session_id,
                local_session_id=local_session_id,
                transport=transport,
                can_reconnect=True,
                connected_at=_now_utc(),
                last_heartbeat_at=_now_utc(),
            )
        )

    def connect_bridge(
        self,
        *,
        session_url: str,
        local_session_id: str,
        remote_session_id: str | None = None,
        detail: str | None = None,
    ) -> RemoteStatus:
        return self._set_current(
            RemoteStatus(
                mode="bridge",
                connected=True,
                session_url=session_url,
                detail=detail or "Bridge session",
                remote_session_id=remote_session_id,
                local_session_id=local_session_id,
                transport="bridge",
                can_reconnect=True,
                connected_at=_now_utc(),
                last_heartbeat_at=_now_utc(),
            )
        )

    def connect_ssh(
        self,
        *,
        host: str,
        local_session_id: str,
        remote_cwd: str | None = None,
        remote_session_id: str | None = None,
        detail: str | None = None,
    ) -> RemoteStatus:
        return self._set_current(
            RemoteStatus(
                mode="ssh",
                connected=True,
                session_url=f"ssh://{host}",
                detail=detail or f"SSH session ({remote_cwd or '~'})",
                remote_session_id=remote_session_id,
                local_session_id=local_session_id,
                transport="ssh",
                can_reconnect=True,
                connected_at=_now_utc(),
                last_heartbeat_at=_now_utc(),
            )
        )

    def hydrate(
        self,
        *,
        local_session_id: str,
        remote_session_id: str | None = None,
        session_url: str | None = None,
        hydrated_from: str,
        detail: str | None = None,
    ) -> RemoteStatus:
        return self._set_current(
            RemoteStatus(
                mode="bridge",
                connected=False,
                session_url=session_url,
                detail=detail or "Hydrated remote transcript",
                remote_session_id=remote_session_id,
                local_session_id=local_session_id,
                transport="hydrate",
                can_reconnect=bool(session_url),
                hydrated_from=hydrated_from,
            )
        )

    def disconnect(self, *, detail: str | None = None) -> RemoteStatus:
        document = self._load()
        current = document.current
        if current.mode == "local":
            return current.model_copy(deep=True)
        document.current = current.model_copy(
            update={
                "connected": False,
                "detail": detail or current.detail,
                "can_reconnect": True,
            }
        )
        self._save(document)
        return document.current.model_copy(deep=True)

    def reconnect(self) -> RemoteStatus:
        document = self._load()
        current = document.current
        if current.mode == "local":
            return current.model_copy(deep=True)
        document.current = current.model_copy(
            update={
                "connected": True,
                "can_reconnect": True,
                "connected_at": current.connected_at or _now_utc(),
                "last_heartbeat_at": _now_utc(),
            }
        )
        self._save(document)
        return document.current.model_copy(deep=True)

    def heartbeat(self) -> RemoteStatus:
        document = self._load()
        current = document.current
        if current.mode == "local":
            return current.model_copy(deep=True)
        document.current = current.model_copy(
            update={
                "last_heartbeat_at": _now_utc(),
            }
        )
        self._save(document)
        return document.current.model_copy(deep=True)

    def archive(self) -> ArchivedRemoteSession | None:
        document = self._load()
        current = document.current
        if current.mode == "local":
            return None
        archived = ArchivedRemoteSession(
            mode=current.mode,
            session_url=current.session_url,
            detail=current.detail,
            remote_session_id=current.remote_session_id,
            local_session_id=current.local_session_id,
            transport=current.transport,
            archived_at=_now_utc(),
            last_heartbeat_at=current.last_heartbeat_at,
            hydrated_from=current.hydrated_from,
        )
        document.archived.insert(0, archived)
        document.archived = document.archived[:50]
        document.current = RemoteStatus(
            mode="local",
            connected=False,
            session_url=None,
            detail="Local session",
            transport="none",
        )
        self._save(document)
        return archived.model_copy(deep=True)

    def archived_sessions(self) -> list[ArchivedRemoteSession]:
        return [item.model_copy(deep=True) for item in self._load().archived]

    def _load(self) -> RemoteStateDocument:
        if not self._path.exists():
            return RemoteStateDocument(
                current=RemoteStatus(
                    mode="local",
                    connected=False,
                    session_url=None,
                    detail="Local session",
                    transport="none",
                )
            )
        try:
            raw = from_json(self._path.read_text(encoding="utf-8"))
        except Exception:
            return RemoteStateDocument()
        if not isinstance(raw, dict):
            return RemoteStateDocument()
        try:
            return RemoteStateDocument.model_validate(raw)
        except Exception:
            return RemoteStateDocument()

    def _save(self, document: RemoteStateDocument) -> None:
        self._path.write_text(
            to_json(document.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )

    def _set_current(self, status: RemoteStatus) -> RemoteStatus:
        document = self._load()
        document.current = status
        self._save(document)
        return status.model_copy(deep=True)
