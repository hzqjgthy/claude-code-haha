from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from claude_code_py.common.ids import new_session_id
from claude_code_py.domain.messages import Message

SessionStatus = Literal["idle", "running", "completed", "failed"]


def _now_utc() -> datetime:
    return datetime.now(UTC)


class SessionMetadata(BaseModel):
    session_id: str = Field(default_factory=new_session_id)
    parent_session_id: str | None = None
    title: str = "Untitled session"
    status: SessionStatus = "idle"
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class SessionState(BaseModel):
    metadata: SessionMetadata
    messages: list[Message] = Field(default_factory=list)


class SessionSummary(BaseModel):
    session_id: str
    title: str
    status: SessionStatus = "idle"
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    first_user_message: str | None = None
    last_user_message: str | None = None
    last_assistant_message: str | None = None
    transcript_path: str
    parent_session_id: str | None = None
