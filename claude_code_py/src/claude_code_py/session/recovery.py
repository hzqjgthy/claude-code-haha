from pydantic import BaseModel

from claude_code_py.domain.sessions import SessionMetadata, SessionState, SessionSummary


class RecoveryRequest(BaseModel):
    session_id: str | None = None
    resume_session_id: str | None = None
    continue_latest: bool = False
    fork_session: bool = False


class RecoveryOutcome(BaseModel):
    state: SessionState
    source_summary: SessionSummary | None = None


def build_recovered_state(
    metadata: SessionMetadata,
    messages: list,
    *,
    source_summary: SessionSummary | None = None,
) -> RecoveryOutcome:
    return RecoveryOutcome(
        state=SessionState(metadata=metadata, messages=messages),
        source_summary=source_summary,
    )
