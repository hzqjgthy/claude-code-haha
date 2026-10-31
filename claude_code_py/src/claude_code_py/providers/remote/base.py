from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


RemoteMode = Literal["local", "remote", "direct_connect", "ssh", "bridge"]
RemoteTransport = Literal[
    "none",
    "websocket",
    "ssh",
    "bridge",
    "hydrate",
    "subprocess",
]


def _now_utc() -> datetime:
    return datetime.now(UTC)


class RemoteStatus(BaseModel):
    mode: RemoteMode = "local"
    connected: bool = False
    session_url: str | None = None
    detail: str | None = None
    remote_session_id: str | None = None
    local_session_id: str | None = None
    transport: RemoteTransport = "none"
    can_reconnect: bool = False
    connected_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    archived_at: datetime | None = None
    hydrated_from: str | None = None


class ArchivedRemoteSession(BaseModel):
    mode: RemoteMode
    session_url: str | None = None
    detail: str | None = None
    remote_session_id: str | None = None
    local_session_id: str | None = None
    transport: RemoteTransport = "none"
    archived_at: datetime = Field(default_factory=_now_utc)
    last_heartbeat_at: datetime | None = None
    hydrated_from: str | None = None


class RemoteProvider(ABC):
    @abstractmethod
    def status(self) -> RemoteStatus:
        raise NotImplementedError

    @abstractmethod
    def connect_direct(
        self,
        *,
        session_url: str,
        local_session_id: str,
        remote_session_id: str | None = None,
        transport: RemoteTransport = "websocket",
        detail: str | None = None,
    ) -> RemoteStatus:
        raise NotImplementedError

    @abstractmethod
    def connect_bridge(
        self,
        *,
        session_url: str,
        local_session_id: str,
        remote_session_id: str | None = None,
        detail: str | None = None,
    ) -> RemoteStatus:
        raise NotImplementedError

    @abstractmethod
    def connect_ssh(
        self,
        *,
        host: str,
        local_session_id: str,
        remote_cwd: str | None = None,
        remote_session_id: str | None = None,
        detail: str | None = None,
    ) -> RemoteStatus:
        raise NotImplementedError

    @abstractmethod
    def hydrate(
        self,
        *,
        local_session_id: str,
        remote_session_id: str | None = None,
        session_url: str | None = None,
        hydrated_from: str,
        detail: str | None = None,
    ) -> RemoteStatus:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self, *, detail: str | None = None) -> RemoteStatus:
        raise NotImplementedError

    @abstractmethod
    def reconnect(self) -> RemoteStatus:
        raise NotImplementedError

    @abstractmethod
    def heartbeat(self) -> RemoteStatus:
        raise NotImplementedError

    @abstractmethod
    def archive(self) -> ArchivedRemoteSession | None:
        raise NotImplementedError

    @abstractmethod
    def archived_sessions(self) -> list[ArchivedRemoteSession]:
        raise NotImplementedError
