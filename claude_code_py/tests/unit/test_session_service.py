from claude_code_py.application.session_service import SessionService
from claude_code_py.domain.messages import AssistantMessage, UserMessage
from claude_code_py.providers.storage.session_index import SqliteSessionIndex
from claude_code_py.providers.storage.transcript_store import JsonlTranscriptStore
from claude_code_py.session.recovery import RecoveryRequest
from tests.helpers import make_test_container


def test_session_service_lists_sessions_after_append(tmp_path) -> None:
    container = make_test_container(tmp_path)
    service = SessionService(
        JsonlTranscriptStore(container.paths),
        SqliteSessionIndex(container.paths.session_index_path),
    )

    state = service.load_or_create("sess-1")
    state = service.append_turn(
        state,
        [UserMessage(content="hello"), AssistantMessage(content="world")],
    )
    sessions = service.list_sessions()

    assert state.metadata.title == "hello"
    assert len(sessions) == 1
    assert sessions[0].session_id == "sess-1"
    assert sessions[0].message_count == 2
    assert sessions[0].title == "hello"


def test_session_service_can_continue_latest_session(tmp_path) -> None:
    container = make_test_container(tmp_path)
    service = SessionService(
        JsonlTranscriptStore(container.paths),
        SqliteSessionIndex(container.paths.session_index_path),
    )

    first = service.load_or_create("sess-1")
    service.append_turn(
        first,
        [UserMessage(content="hello"), AssistantMessage(content="world")],
    )

    recovered = service.recover(RecoveryRequest(continue_latest=True))

    assert recovered.state.metadata.session_id == "sess-1"
    assert len(recovered.state.messages) == 2
    assert recovered.state.messages[0].kind == "user"


def test_session_service_can_fork_from_existing_session(tmp_path) -> None:
    container = make_test_container(tmp_path)
    service = SessionService(
        JsonlTranscriptStore(container.paths),
        SqliteSessionIndex(container.paths.session_index_path),
    )

    original = service.load_or_create("sess-1")
    service.append_turn(
        original,
        [UserMessage(content="hello"), AssistantMessage(content="world")],
    )

    forked = service.recover(
        RecoveryRequest(resume_session_id="sess-1", fork_session=True),
    )

    assert forked.state.metadata.session_id != "sess-1"
    assert forked.state.metadata.parent_session_id == "sess-1"
    assert len(forked.state.messages) == 2


def test_session_service_backfills_index_from_existing_transcript(tmp_path) -> None:
    container = make_test_container(tmp_path)
    transcript_store = JsonlTranscriptStore(container.paths)
    transcript_store.append_messages(
        "legacy-1",
        [UserMessage(content="legacy hello"), AssistantMessage(content="legacy world")],
    )
    service = SessionService(
        transcript_store,
        SqliteSessionIndex(container.paths.session_index_path),
    )

    sessions = service.list_sessions()

    assert len(sessions) == 1
    assert sessions[0].session_id == "legacy-1"
    assert sessions[0].title == "legacy hello"
