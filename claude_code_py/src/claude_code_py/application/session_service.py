from datetime import UTC, datetime

from claude_code_py.domain.messages import Message
from claude_code_py.domain.sessions import SessionMetadata, SessionState, SessionSummary
from claude_code_py.providers.storage.session_index import SqliteSessionIndex
from claude_code_py.providers.storage.transcript_store import JsonlTranscriptStore
from claude_code_py.session.history import SessionHistorySnapshot, build_history_snapshot
from claude_code_py.session.recovery import RecoveryOutcome, RecoveryRequest, build_recovered_state
from claude_code_py.session.transcript import summarize_session, touch_metadata


class SessionService:
    def __init__(
        self,
        transcript_store: JsonlTranscriptStore,
        session_index: SqliteSessionIndex,
    ) -> None:
        self._transcript_store = transcript_store
        self._session_index = session_index

    def load_or_create(self, session_id: str | None = None) -> SessionState:
        outcome = self.recover(RecoveryRequest(session_id=session_id))
        return outcome.state

    def recover(self, request: RecoveryRequest) -> RecoveryOutcome:
        self._validate_request(request)

        if request.continue_latest:
            latest = self.latest_session()
            if latest is None:
                raise RuntimeError("No previous session found to continue.")
            return self._load_existing_session(latest.session_id, fork=request.fork_session)

        if request.resume_session_id:
            return self._load_existing_session(
                request.resume_session_id,
                fork=request.fork_session,
            )

        if request.session_id:
            if self._transcript_store.exists(request.session_id):
                return self._load_existing_session(
                    request.session_id,
                    fork=request.fork_session,
                )
            metadata = SessionMetadata(session_id=request.session_id)
            return build_recovered_state(metadata, [])

        metadata = SessionMetadata()
        return build_recovered_state(metadata, [])

    def append_turn(self, state: SessionState, messages: list[Message]) -> SessionState:
        if not messages:
            return state

        self._transcript_store.append_messages(state.metadata.session_id, messages)
        all_messages = [*state.messages, *messages]
        updated_metadata = touch_metadata(
            state.metadata,
            all_messages,
            status="completed",
        )
        summary = summarize_session(
            updated_metadata,
            all_messages,
            transcript_path=str(
                self._transcript_store.transcript_path(updated_metadata.session_id),
            ),
        )
        self._session_index.upsert(summary)
        return SessionState(metadata=updated_metadata, messages=all_messages)

    def list_sessions(self, *, limit: int = 20) -> list[SessionSummary]:
        indexed = {summary.session_id: summary for summary in self._session_index.list_recent(limit=limit)}
        for session_id in self._transcript_store.list_session_ids():
            if session_id in indexed:
                continue
            indexed[session_id] = self._build_summary_from_transcript(session_id)
            self._session_index.upsert(indexed[session_id])
        summaries = sorted(
            indexed.values(),
            key=lambda summary: summary.updated_at,
            reverse=True,
        )
        return summaries[:limit]

    def latest_session(self) -> SessionSummary | None:
        sessions = self.list_sessions(limit=1)
        return sessions[0] if sessions else None

    def get_history(self, session_id: str) -> SessionHistorySnapshot:
        summary = self._load_summary(session_id)
        messages = self._transcript_store.load_messages(session_id)
        return build_history_snapshot(summary, messages)

    def rename_session(self, state: SessionState, title: str) -> SessionState:
        normalized_title = " ".join(title.strip().split())
        if not normalized_title:
            raise ValueError("Session title cannot be empty.")

        updated_metadata = state.metadata.model_copy(
            update={
                "title": normalized_title,
                "updated_at": datetime.now(UTC),
            },
        )
        summary = summarize_session(
            updated_metadata,
            state.messages,
            transcript_path=str(
                self._transcript_store.transcript_path(updated_metadata.session_id),
            ),
        )
        self._session_index.upsert(summary)
        return SessionState(metadata=updated_metadata, messages=list(state.messages))

    def rewrite_messages(
        self,
        state: SessionState,
        messages: list[Message],
    ) -> SessionState:
        self._transcript_store.overwrite_messages(
            state.metadata.session_id,
            messages,
        )
        updated_metadata = state.metadata.model_copy(
            update={
                "updated_at": datetime.now(UTC),
                "status": "completed",
            },
        )
        summary = summarize_session(
            updated_metadata,
            messages,
            transcript_path=str(
                self._transcript_store.transcript_path(updated_metadata.session_id),
            ),
        )
        self._session_index.upsert(summary)
        return SessionState(metadata=updated_metadata, messages=list(messages))

    def _load_existing_session(
        self,
        session_id: str,
        *,
        fork: bool,
    ) -> RecoveryOutcome:
        if not self._transcript_store.exists(session_id):
            raise RuntimeError(f"Session '{session_id}' was not found.")

        messages = self._transcript_store.load_messages(session_id)
        summary = self._load_summary(session_id, messages=messages)

        if fork:
            metadata = SessionMetadata(
                title=summary.title,
                parent_session_id=summary.session_id,
            )
            return build_recovered_state(
                metadata,
                messages,
                source_summary=summary,
            )

        metadata = SessionMetadata(
            session_id=summary.session_id,
            parent_session_id=summary.parent_session_id,
            title=summary.title,
            status=summary.status,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
        )
        return build_recovered_state(metadata, messages, source_summary=summary)

    def _load_summary(
        self,
        session_id: str,
        *,
        messages: list[Message] | None = None,
    ) -> SessionSummary:
        summary = self._session_index.get(session_id)
        if summary is not None:
            return summary
        fallback = self._build_summary_from_transcript(session_id, messages=messages)
        self._session_index.upsert(fallback)
        return fallback

    def _build_summary_from_transcript(
        self,
        session_id: str,
        *,
        messages: list[Message] | None = None,
    ) -> SessionSummary:
        transcript_messages = messages or self._transcript_store.load_messages(session_id)
        transcript_path = self._transcript_store.transcript_path(session_id)
        created_at = _message_timestamp(transcript_messages, "first")
        updated_at = _message_timestamp(transcript_messages, "last")
        metadata = SessionMetadata(
            session_id=session_id,
            status="completed",
            created_at=created_at,
            updated_at=updated_at,
        )
        return summarize_session(
            metadata,
            transcript_messages,
            transcript_path=str(transcript_path),
        )

    @staticmethod
    def _validate_request(request: RecoveryRequest) -> None:
        if request.continue_latest and request.resume_session_id:
            raise ValueError("Cannot use continue_latest and resume_session_id together.")
        if request.fork_session and not (
            request.continue_latest
            or request.resume_session_id
            or request.session_id
        ):
            raise ValueError("fork_session requires an existing source session.")


def _message_timestamp(messages: list[Message], position: str) -> datetime:
    if not messages:
        return datetime.now(UTC)
    if position == "first":
        return messages[0].created_at
    return messages[-1].created_at
