from pydantic import BaseModel, Field

from claude_code_py.domain.messages import Message
from claude_code_py.domain.sessions import SessionSummary


class SessionHistorySnapshot(BaseModel):
    summary: SessionSummary
    messages: list[Message] = Field(default_factory=list)


def build_history_snapshot(
    summary: SessionSummary,
    messages: list[Message],
) -> SessionHistorySnapshot:
    return SessionHistorySnapshot(summary=summary, messages=messages)
