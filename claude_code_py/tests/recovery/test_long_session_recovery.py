from tests.helpers import make_test_container

from claude_code_py.application.session_service import SessionService
from claude_code_py.domain.messages import AssistantMessage, UserMessage
from claude_code_py.providers.storage.session_index import SqliteSessionIndex
from claude_code_py.providers.storage.transcript_store import JsonlTranscriptStore
from claude_code_py.session.recovery import RecoveryRequest


def test_recovery_handles_long_transcript_resume_and_fork(tmp_path) -> None:
    container = make_test_container(tmp_path)
    service = SessionService(
        JsonlTranscriptStore(container.paths),
        SqliteSessionIndex(container.paths.session_index_path),
    )

    state = service.load_or_create("sess-long")
    for index in range(150):
        state = service.append_turn(
            state,
            [
                UserMessage(content=f"user turn {index}"),
                AssistantMessage(content=f"assistant turn {index}"),
            ],
        )

    continued = service.recover(RecoveryRequest(continue_latest=True))
    forked = service.recover(
        RecoveryRequest(resume_session_id="sess-long", fork_session=True),
    )
    sessions = service.list_sessions(limit=5)

    assert continued.state.metadata.session_id == "sess-long"
    assert len(continued.state.messages) == 300
    assert continued.state.messages[-1].content == "assistant turn 149"  # type: ignore[attr-defined]

    assert forked.state.metadata.session_id != "sess-long"
    assert forked.state.metadata.parent_session_id == "sess-long"
    assert len(forked.state.messages) == 300
    assert forked.source_summary is not None
    assert forked.source_summary.message_count == 300

    assert sessions[0].session_id == "sess-long"
    assert sessions[0].message_count == 300
    assert sessions[0].title == "user turn 0"
