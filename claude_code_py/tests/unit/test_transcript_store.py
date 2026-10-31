from claude_code_py.domain.messages import AssistantMessage, UserMessage
from claude_code_py.providers.storage.transcript_store import JsonlTranscriptStore
from tests.helpers import make_test_container


def test_transcript_store_roundtrip(tmp_path) -> None:
    container = make_test_container(tmp_path)
    store = JsonlTranscriptStore(container.paths)
    messages = [UserMessage(content="hello"), AssistantMessage(content="world")]

    store.append_messages("sess-1", messages)
    loaded = store.load_messages("sess-1")

    assert len(loaded) == 2
    assert loaded[0].kind == "user"
    assert loaded[1].kind == "assistant"
