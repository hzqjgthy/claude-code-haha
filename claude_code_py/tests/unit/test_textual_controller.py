from pathlib import Path

from tests.helpers import make_test_container

from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.ui.textual.controller import TextualSessionController


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


def test_textual_controller_submits_prompt_and_tracks_status(
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
        entries = controller.submit_prompt("hello")

        assert [entry.kind for entry in entries] == ["user", "assistant"]
        assert entries[-1].text == "assistant:hello"
        assert controller.task_summary_lines() == ["No tasks"]
        snapshot = controller.status_snapshot()
        assert snapshot.session_id == "sess-1"
        assert snapshot.remote_status.mode == "local"
        assert controller.permission_summary_lines()[0] == "permission_mode: default"
    finally:
        controller.shutdown()


def test_textual_controller_supports_slash_commands(
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
        entries = controller.submit_prompt("/model upgraded-model")

        assert len(entries) == 1
        assert entries[0].kind == "system"
        assert entries[0].text == "Model updated to upgraded-model"
        assert controller.status_snapshot().model == "upgraded-model"
    finally:
        controller.shutdown()
