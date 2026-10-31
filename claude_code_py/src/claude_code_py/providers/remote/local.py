from datetime import UTC, datetime

from claude_code_py.providers.remote.base import (
    ArchivedRemoteSession,
    RemoteProvider,
    RemoteTransport,
    RemoteStatus,
)


class LocalRemoteProvider(RemoteProvider):
    def __init__(self) -> None:
        self._status = RemoteStatus(
            mode="local",
            connected=False,
            session_url=None,
            detail="Local session",
            transport="none",
        )

    def status(self) -> RemoteStatus:
        return self._status.model_copy(deep=True)

    def connect_direct(
        self,
        *,
        session_url: str,
        local_session_id: str,
        remote_session_id: str | None = None,
        transport: RemoteTransport = "websocket",
        detail: str | None = None,
    ) -> RemoteStatus:
        self._status = RemoteStatus(
            mode="direct_connect",
            connected=True,
            session_url=session_url,
            detail=detail or "Direct connect session",
            remote_session_id=remote_session_id,
            local_session_id=local_session_id,
            transport=transport,
            can_reconnect=True,
            connected_at=datetime.now(UTC),
            last_heartbeat_at=datetime.now(UTC),
        )
        return self.status()

    def connect_bridge(
        self,
        *,
        session_url: str,
        local_session_id: str,
        remote_session_id: str | None = None,
        detail: str | None = None,
    ) -> RemoteStatus:
        self._status = RemoteStatus(
            mode="bridge",
            connected=True,
            session_url=session_url,
            detail=detail or "Bridge session",
            remote_session_id=remote_session_id,
            local_session_id=local_session_id,
            transport="bridge",
            can_reconnect=True,
            connected_at=datetime.now(UTC),
            last_heartbeat_at=datetime.now(UTC),
        )
        return self.status()

    def connect_ssh(
        self,
        *,
        host: str,
        local_session_id: str,
        remote_cwd: str | None = None,
        remote_session_id: str | None = None,
        detail: str | None = None,
    ) -> RemoteStatus:
        self._status = RemoteStatus(
            mode="ssh",
            connected=True,
            session_url=f"ssh://{host}",
            detail=detail or f"SSH session ({remote_cwd or '~'})",
            remote_session_id=remote_session_id,
            local_session_id=local_session_id,
            transport="ssh",
            can_reconnect=True,
            connected_at=datetime.now(UTC),
            last_heartbeat_at=datetime.now(UTC),
        )
        return self.status()

    def hydrate(
        self,
        *,
        local_session_id: str,
        remote_session_id: str | None = None,
        session_url: str | None = None,
        hydrated_from: str,
        detail: str | None = None,
    ) -> RemoteStatus:
        self._status = RemoteStatus(
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
        return self.status()

    def disconnect(self, *, detail: str | None = None) -> RemoteStatus:
        self._status = self._status.model_copy(
            update={
                "connected": False,
                "detail": detail or self._status.detail,
                "can_reconnect": self._status.mode != "local",
            }
        )
        return self.status()

    def reconnect(self) -> RemoteStatus:
        if self._status.mode == "local":
            return self.status()
        self._status = self._status.model_copy(
            update={
                "connected": True,
                "can_reconnect": True,
            }
        )
        return self.status()

    def heartbeat(self) -> RemoteStatus:
        if self._status.mode == "local":
            return self.status()
        self._status = self._status.model_copy(
            update={
                "last_heartbeat_at": datetime.now(UTC),
            }
        )
        return self.status()

    def archive(self) -> ArchivedRemoteSession | None:
        if self._status.mode == "local":
            return None
        archived = ArchivedRemoteSession(
            mode=self._status.mode,
            session_url=self._status.session_url,
            detail=self._status.detail,
            remote_session_id=self._status.remote_session_id,
            local_session_id=self._status.local_session_id,
            transport=self._status.transport,
            last_heartbeat_at=self._status.last_heartbeat_at,
            hydrated_from=self._status.hydrated_from,
        )
        self._status = RemoteStatus(
            mode="local",
            connected=False,
            session_url=None,
            detail="Local session",
            transport="none",
        )
        return archived

    def archived_sessions(self) -> list[ArchivedRemoteSession]:
        return []
