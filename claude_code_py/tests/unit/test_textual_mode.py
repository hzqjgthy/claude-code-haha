import asyncio
from pathlib import Path

from tests.helpers import make_test_container

from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.cli.textual_mode import run_textual_mode
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.ui.textual.app import ClaudeCodeTextualApp


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


def test_run_textual_mode_loads_app_lazily(monkeypatch, tmp_path: Path) -> None:
    container = make_test_container(tmp_path)
    captured: dict[str, object] = {}

    class FakeTextualApp:
        def __init__(
            self, container_arg, params_arg, *, provider=None, remote_provider=None
        ):
            captured["container"] = container_arg
            captured["params"] = params_arg
            captured["provider"] = provider
            captured["remote_provider"] = remote_provider
            captured["shutdown_calls"] = 0

        def run(self) -> int:
            return 7

        def shutdown_runtime(self) -> None:
            captured["shutdown_calls"] = int(captured["shutdown_calls"]) + 1

    monkeypatch.setattr(
        "claude_code_py.cli.textual_mode._load_textual_app_class",
        lambda: FakeTextualApp,
    )

    exit_code = run_textual_mode(
        container,
        ReplModeParams(session_id="sess-1"),
    )

    assert exit_code == 7
    assert captured["container"] is container
    assert captured["params"].session_id == "sess-1"
    assert captured["shutdown_calls"] == 1


def test_textual_app_supports_arrow_selection_and_tab_completion(
    monkeypatch,
    tmp_path: Path,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    app = ClaudeCodeTextualApp(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    async def run_scenario() -> None:
        async with app.run_test() as pilot:
            await pilot.press("/")
            await pilot.press("down")
            assert app._runtime.store.get_state().prompt.selected_suggestion == 1
            await pilot.press("tab")
            input_widget = app.query_one("#composer-input")
            assert input_widget.value == "/status "

    asyncio.run(run_scenario())


def test_textual_app_can_copy_transcript_to_clipboard(
    monkeypatch,
    tmp_path: Path,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    copied: dict[str, str] = {}

    def fake_copy_text_to_clipboard(text: str, *, osc52_fallback=None) -> str:
        del osc52_fallback
        copied["text"] = text
        return "test-backend"

    monkeypatch.setattr(
        "claude_code_py.ui.textual.app.copy_text_to_clipboard",
        fake_copy_text_to_clipboard,
    )

    app = ClaudeCodeTextualApp(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    async def run_scenario() -> None:
        async with app.run_test() as pilot:
            app._runtime.controller.append_ui_entry("user", "copy me")
            app._runtime.controller.append_ui_entry("assistant", "copied response")
            app._refresh_runtime()
            await pilot.press("f6")
            assert "> copy me" in copied["text"]
            assert "copied response" in copied["text"]

    asyncio.run(run_scenario())


def test_textual_layout_keeps_transcript_full_height_without_dialogs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    app = ClaudeCodeTextualApp(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    async def run_scenario() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            del pilot
            layout = app.query_one("#fullscreen-layout")
            scroll_region = layout.query_one("#scroll-region")
            transcript = layout.query_one("#transcript")
            assert transcript.region.height == scroll_region.region.height

    asyncio.run(run_scenario())


def test_textual_transcript_can_scroll_long_history(
    monkeypatch,
    tmp_path: Path,
) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    app = ClaudeCodeTextualApp(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    async def run_scenario() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            for index in range(60):
                app._runtime.controller.append_ui_entry(
                    "assistant",
                    f"history line {index}",
                )
            app._refresh_runtime()
            await pilot.pause()
            transcript = app.query_one("#transcript")
            assert transcript.max_scroll_y > 0

    asyncio.run(run_scenario())
