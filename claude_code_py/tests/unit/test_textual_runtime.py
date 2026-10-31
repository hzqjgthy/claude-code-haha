from pathlib import Path

from tests.helpers import make_test_container

from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.ui.runtime import TextualReplRuntime


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


def test_textual_repl_runtime_exposes_stateful_runtime_flow(
    tmp_path: Path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    runtime = TextualReplRuntime(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        initial = runtime.refresh()
        assert initial.status is not None
        assert initial.status.session_id == "sess-1"
        assert initial.runtime_message == "Idle"

        help_state = runtime.show_help()
        assert help_state.info_dialog is not None
        assert help_state.info_dialog.kind == "help"

        cleared = runtime.clear_info_dialog()
        assert cleared.info_dialog is None

        runtime.submit_prompt("hello")
        after_submit = runtime.store.get_state()
        assert after_submit.runtime_message == "Idle"
        assert after_submit.is_submitting is False
        assert [entry.kind for entry in after_submit.transcript[-2:]] == [
            "user",
            "assistant",
        ]
        assert after_submit.transcript[-1].text == "assistant:hello"

        runtime.submit_prompt("/status")
        after_command = runtime.store.get_state()
        assert after_command.info_dialog is not None
        assert after_command.info_dialog.kind == "command:status"
        assert after_command.info_dialog.title == "Status"

        runtime.update_prompt_text("/")
        prompt_state = runtime.store.get_state().prompt
        assert len(prompt_state.suggestions) > 1
        assert prompt_state.selected_suggestion == 0

        runtime.cycle_prompt_suggestion(1)
        cycled_state = runtime.store.get_state().prompt
        assert cycled_state.selected_suggestion == 1

        runtime.refresh()
        refreshed_state = runtime.store.get_state().prompt
        assert refreshed_state.selected_suggestion == 1

        runtime.update_prompt_text("/")
        updated_state = runtime.store.get_state().prompt
        assert updated_state.selected_suggestion == 1

        applied_text = runtime.apply_selected_prompt_suggestion()
        assert applied_text.startswith("/")
        assert runtime.store.get_state().prompt.text == applied_text

        runtime.clear_info_dialog()
        runtime.submit_prompt("/memory")
        memory_state = runtime.store.get_state()
        assert memory_state.selector_dialog is not None
        assert memory_state.selector_dialog.kind == "selector:memory"
        assert any(
            option.command == "/memory edit project"
            for option in memory_state.selector_dialog.options
        )
        assert memory_state.info_dialog is None

        runtime.clear_selector_dialog()
        runtime.submit_prompt("/memory edit project")
        editor_state = runtime.store.get_state()
        assert editor_state.editor_dialog is not None
        assert editor_state.editor_dialog.kind == "memory-editor"
        assert editor_state.editor_dialog.title == "Edit Memory: Project memory"

        runtime.save_editor_dialog("# remembered\n")
        saved_path = workspace_root / "CLAUDE.md"
        assert saved_path.read_text(encoding="utf-8") == "# remembered\n"
        assert runtime.store.get_state().editor_dialog is None

        runtime.clear_info_dialog()
        runtime.submit_prompt("first turn")
        runtime.submit_prompt("second turn")
        runtime.submit_prompt("/rewind")
        rewind_state = runtime.store.get_state()
        assert rewind_state.selector_dialog is not None
        assert rewind_state.selector_dialog.kind == "selector:rewind"
        assert any(
            option.command == "/rewind 2"
            for option in rewind_state.selector_dialog.options
        )
    finally:
        runtime.shutdown()


def test_textual_repl_runtime_clears_stale_info_dialog_on_new_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    runtime = TextualReplRuntime(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        help_state = runtime.show_help()
        assert help_state.info_dialog is not None
        assert help_state.info_dialog.kind == "help"

        runtime.submit_prompt("/model upgraded-model")
        state = runtime.store.get_state()

        assert state.info_dialog is None
        assert state.editor_dialog is None
        assert state.selector_dialog is None
        assert state.transcript[-1].text == "Model updated to upgraded-model"
    finally:
        runtime.shutdown()
