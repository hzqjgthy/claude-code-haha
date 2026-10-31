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


class RecordingProvider(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        prompt = request.messages[-1].content  # type: ignore[union-attr]
        return CompletionResponse(
            model=request.model,
            text=f"{request.model}:{prompt}",
            raw_response={"model": request.model},
        )


class TargetedPermissionProvider(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if request.messages and request.messages[-1].kind == "tool_result":
            return CompletionResponse(
                model=request.model,
                text="permission-flow-complete",
                raw_response={"phase": "assistant"},
            )

        prompt = request.messages[-1].content  # type: ignore[union-attr]
        file_path = "notes/alpha.txt" if "alpha" in prompt else "notes/beta.txt"
        return CompletionResponse(
            model=request.model,
            stop_reason="tool_use",
            tool_calls=[
                ToolCall(
                    tool_use_id=f"toolu_{len(self.requests)}",
                    tool_name="Write",
                    arguments={"file_path": file_path, "content": prompt},
                )
            ],
            raw_response={"phase": "tool"},
        )


def test_repl_command_contract_matches_original_flow(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = RecordingProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    controller = TextualSessionController(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
    )

    try:
        first = controller.submit_prompt("hello")
        assert first[-1].text == "test-model:hello"

        controller.submit_prompt("/model parity-model")
        second = controller.submit_prompt("follow up")
        assert second[-1].text == "parity-model:follow up"
        assert provider.requests[-1].model == "parity-model"

        clear_result = controller.submit_prompt("/clear")
        cleared_session_id = controller.status_snapshot().session_id
        assert cleared_session_id != "sess-1"
        assert "Started a new session" in clear_result[0].text

        resume_result = controller.submit_prompt("/resume sess-1 --fork")
        forked_session_id = controller.status_snapshot().session_id
        assert forked_session_id not in {"sess-1", cleared_session_id}
        assert "Forked from session sess-1" in resume_result[0].text

        third = controller.submit_prompt("fork follow up")
        assert third[-1].text == "parity-model:fork follow up"
        assert len(provider.requests[-1].messages) >= 4
    finally:
        controller.shutdown()


def test_permission_contract_remembers_session_approval_per_target(
    tmp_path,
    monkeypatch,
) -> None:
    container = make_test_container(tmp_path)
    provider = TargetedPermissionProvider()
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

    def run_prompt(prompt: str, bucket: dict[str, object], key: str) -> Thread:
        worker = Thread(
            target=lambda: bucket.__setitem__(key, controller.submit_prompt(prompt))
        )
        worker.start()
        return worker

    def wait_for_permission() -> str:
        deadline = time() + 2
        pending = controller.pending_permission_request()
        while pending is None and time() < deadline:
            sleep(0.01)
            pending = controller.pending_permission_request()
        assert pending is not None
        return pending.summary

    results: dict[str, object] = {}

    try:
        alpha_worker = run_prompt("write alpha note", results, "alpha_first")
        assert wait_for_permission() == "notes/alpha.txt"
        assert controller.resolve_permission_request("allow_session") is True
        alpha_worker.join(timeout=2)
        assert alpha_worker.is_alive() is False
        assert controller.pending_permission_request() is None

        alpha_again = controller.submit_prompt("write alpha note again")
        assert alpha_again[-1].text == "permission-flow-complete"
        assert controller.pending_permission_request() is None

        beta_worker = run_prompt("write beta note", results, "beta_first")
        assert wait_for_permission() == "notes/beta.txt"
        assert controller.resolve_permission_request("deny_once") is True
        beta_worker.join(timeout=2)
        assert beta_worker.is_alive() is False
        assert controller.pending_permission_request() is None
    finally:
        controller.shutdown()
