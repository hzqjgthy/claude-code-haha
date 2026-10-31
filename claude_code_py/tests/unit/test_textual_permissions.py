from threading import Thread
from time import sleep, time

from tests.helpers import make_test_container

from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.domain.tools import ToolCall
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.ui.textual.controller import TextualSessionController


class PermissionToolLoopProvider(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if request.messages and request.messages[-1].kind == "tool_result":
            return CompletionResponse(
                model=request.model,
                text="finished after permission",
                raw_response={"phase": "assistant"},
            )

        return CompletionResponse(
            model=request.model,
            stop_reason="tool_use",
            tool_calls=[
                ToolCall(
                    tool_use_id="toolu_1",
                    tool_name="Write",
                    arguments={"file_path": "note.txt", "content": "hello"},
                )
            ],
            raw_response={"phase": "tool"},
        )


def test_textual_controller_supports_interactive_permission_requests(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = PermissionToolLoopProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(
            session_id="sess-1",
            ask_rules=["Write(path:*)"],
        ),
        provider=provider,
    )

    result: dict[str, object] = {}

    def run_prompt() -> None:
        result["entries"] = controller.submit_prompt("write note")

    worker = Thread(target=run_prompt)
    worker.start()

    deadline = time() + 2
    pending = controller.pending_permission_request()
    while pending is None and time() < deadline:
        sleep(0.01)
        pending = controller.pending_permission_request()

    try:
        assert pending is not None
        assert pending.tool_name == "Write"
        assert pending.request_kind == "file_write"
        assert pending.title in {"Create file", "Overwrite file"}
        assert pending.prompt is not None
        assert any("Write(path:" in line for line in pending.target_lines)
        assert pending.preview is not None

        assert controller.resolve_permission_request("allow_session") is True
        worker.join(timeout=2)
        assert worker.is_alive() is False

        entries = result["entries"]
        assert isinstance(entries, list)
        assert entries[-1].text == "finished after permission"

        second_entries = controller.submit_prompt("write note again")
        assert second_entries[-1].text == "finished after permission"
        assert controller.pending_permission_request() is None
    finally:
        controller.shutdown()
