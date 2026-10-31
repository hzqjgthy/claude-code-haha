from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from claude_code_py.common.ids import new_task_id

TaskStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
TaskKind = Literal["agent", "teammate", "workflow", "plugin", "mcp"]


def _now_utc() -> datetime:
    return datetime.now(UTC)


class TaskRecord(BaseModel):
    task_id: str = Field(default_factory=new_task_id)
    kind: TaskKind = "agent"
    description: str
    prompt: str
    status: TaskStatus = "pending"
    background: bool = False
    model: str | None = None
    owner: str | None = None
    session_id: str | None = None
    parent_task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    result_text: str | None = None
    error_message: str | None = None
