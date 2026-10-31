from pathlib import Path

from tests.helpers import make_test_container

from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.providers.remote import RemoteStatus
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.ui.runtime.session_runtime import TextualSessionRuntime
from claude_code_py.ui.state import (
    PermissionRequestState,
    StatusDetailState,
    StatusSnapshot,
    TranscriptEntry,
)
from claude_code_py.ui.textual.controller import TextualSessionController
from claude_code_py.ui.textual.messages import render_transcript_entry
from claude_code_py.ui.textual.widgets.transcript import (
    compute_bottom_padding_lines,
    find_search_matches,
    render_transcript_intro,
    render_transcript_plain_text,
)
from claude_code_py.ui.textual.widgets.prompt_overlay import (
    render_prompt_overlay_suggestions,
)


class FakeProvider(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        prompt = request.messages[-1].content  # type: ignore[union-attr]
        return CompletionResponse(
            model=request.model,
            text=f"assistant:{prompt}",
            raw_response={"model": request.model},
        )


def test_session_runtime_builds_command_prompt_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    runtime = TextualSessionRuntime(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        state = runtime.build_prompt_state("/re")
        assert state.mode == "command"
        assert state.selected_suggestion == 0
        assert any(item.value == "/resume" for item in state.suggestions)
        assert any(item.value == "/review" for item in state.suggestions)
    finally:
        runtime.shutdown()


def test_session_runtime_suggests_alias_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    runtime = TextualSessionRuntime(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        state = runtime.build_prompt_state("/set")
        assert state.mode == "command"
        assert any(item.value == "/settings" for item in state.suggestions)
        assert any(item.value == "/settings" and "alias for /config" in (item.description or "") for item in state.suggestions)
    finally:
        runtime.shutdown()


def test_session_runtime_handles_bare_slash_prompt_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    runtime = TextualSessionRuntime(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        state = runtime.build_prompt_state("/")
        assert state.mode == "command"
        assert state.selected_suggestion == 0
        assert len(state.suggestions) >= 30
        assert any(item.value == "/help" for item in state.suggestions)
        assert any(item.value == "/desktop" for item in state.suggestions)
        assert any(item.value == "/voice" for item in state.suggestions)
    finally:
        runtime.shutdown()


def test_controller_exposes_status_detail_snapshot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        controller.submit_prompt("hello")
        detail = controller.status_detail_snapshot()
        assert detail.project_name == "workspace"
        assert detail.user_entries >= 1
        assert detail.assistant_entries >= 1
        assert detail.command_count >= 1
    finally:
        controller.shutdown()


def test_transcript_renderer_distinguishes_special_entries() -> None:
    tool_call = render_transcript_entry(
        TranscriptEntry("system", "Tool call: Write {'a': 1}")
    )
    permission = render_transcript_entry(
        TranscriptEntry("system", "Permission requested: Write (file.txt)")
    )
    assistant = render_transcript_entry(TranscriptEntry("assistant", "hello"))

    assert "tool:" in tool_call.plain
    assert "permission:" in permission.plain
    assert assistant.plain == "hello"


def test_find_search_matches_returns_matching_entry_indexes() -> None:
    entries = [
        TranscriptEntry("user", "hello world"),
        TranscriptEntry("assistant", "working on it"),
        TranscriptEntry("assistant", "world state"),
    ]

    assert find_search_matches(entries, "world") == [0, 2]
    assert find_search_matches(entries, "missing") == []


def test_compute_bottom_padding_lines_bottom_anchors_short_transcript() -> None:
    assert compute_bottom_padding_lines(content_lines=5, viewport_height=12) == 7
    assert compute_bottom_padding_lines(content_lines=12, viewport_height=12) == 0
    assert compute_bottom_padding_lines(content_lines=20, viewport_height=12) == 0


def test_render_transcript_plain_text_formats_entries_for_copy() -> None:
    entries = [
        TranscriptEntry("user", "first line\nsecond line"),
        TranscriptEntry("assistant", "hello"),
        TranscriptEntry("system", "Tool call: Write {'a': 1}"),
        TranscriptEntry("error", "boom"),
    ]

    rendered = render_transcript_plain_text(entries)

    assert "> first line\n> second line" in rendered
    assert "hello" in rendered
    assert "tool: Tool call: Write {'a': 1}" in rendered
    assert "! boom" in rendered


def test_render_prompt_overlay_suggestions_renders_selected_item() -> None:
    from claude_code_py.ui.state import PromptState, PromptSuggestionState

    rendered = render_prompt_overlay_suggestions(
        PromptState(
            text="/",
            mode="command",
            suggestions=[
                PromptSuggestionState(value="/help", description="Show help"),
                PromptSuggestionState(value="/status", description="Show status"),
            ],
            selected_suggestion=1,
        )
    )

    assert "/help" in rendered.plain
    assert "/status" in rendered.plain
    assert "Show status" in rendered.plain


def test_render_prompt_overlay_suggestions_windows_large_lists() -> None:
    from claude_code_py.ui.state import PromptState, PromptSuggestionState

    rendered = render_prompt_overlay_suggestions(
        PromptState(
            text="/",
            mode="command",
            suggestions=[
                PromptSuggestionState(value=f"/cmd{i}", description=f"command {i}")
                for i in range(12)
            ],
            selected_suggestion=9,
        )
    )

    assert "/cmd9" in rendered.plain
    assert "/cmd0" not in rendered.plain
    assert "..." in rendered.plain


def test_render_transcript_intro_includes_core_status_details() -> None:
    status = StatusSnapshot(
        session_id="sess-12345678",
        model="test-model",
        permission_mode="default",
        remote_status=RemoteStatus(
            mode="remote",
            connected=True,
            detail=None,
            session_url=None,
        ),
    )
    detail = StatusDetailState(
        session_title="Demo Session",
        project_name="workspace",
        cwd_name="workspace",
        transcript_entries=12,
        task_count=2,
    )
    permission_request = PermissionRequestState(
        request_id="req-1",
        tool_name="Write",
        summary="Edit file",
    )

    rendered = render_transcript_intro(
        status=status,
        detail=detail,
        runtime_message="Running: /status",
        permission_request=permission_request,
        task_summary_lines=["task-1 | running | bg=True | indexing"],
    )

    assert "Claude Code" in rendered.plain
    assert "workspace" in rendered.plain
    assert "model test-model" in rendered.plain
    assert "remote connected" in rendered.plain
    assert "running: /status" in rendered.plain
    assert "approval pending" in rendered.plain
    assert "tasks 2" in rendered.plain
