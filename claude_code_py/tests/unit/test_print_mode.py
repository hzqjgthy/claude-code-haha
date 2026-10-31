import json
from io import StringIO
from pathlib import Path

from claude_code_py.cli.print_mode import (
    OutputFormat,
    PrintModeParams,
    build_system_prompt,
    resolve_prompt,
    run_print_mode,
)
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from tests.helpers import make_test_container


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


def test_resolve_prompt_prefers_cli_prompt() -> None:
    merged = resolve_prompt("hello", StringIO("world"))

    assert merged == "hello"


def test_build_system_prompt_supports_append(tmp_path: Path) -> None:
    prompt_file = tmp_path / "system.txt"
    prompt_file.write_text("base prompt", encoding="utf-8")

    rendered = build_system_prompt(None, prompt_file, "extra prompt")

    assert rendered == "base prompt\n\nextra prompt"


def test_run_print_mode_supports_stdin_input(tmp_path: Path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)
    params = PrintModeParams(output_format=OutputFormat.TEXT)

    exit_code, rendered = run_print_mode(
        container,
        params,
        stdin=StringIO("hello from stdin"),
        provider=FakeProvider(),
    )

    assert exit_code == 0
    assert rendered == "assistant:hello from stdin"


def test_run_print_mode_can_render_json(tmp_path: Path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)
    params = PrintModeParams(prompt="hello", output_format=OutputFormat.JSON)

    exit_code, rendered = run_print_mode(
        container,
        params,
        provider=FakeProvider(),
    )

    assert exit_code == 0
    assert '"text": "assistant:hello"' in rendered
    assert '"session_id":' in rendered


def test_run_print_mode_reuses_transcript_history(tmp_path: Path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)
    provider = FakeProvider()

    first_exit_code, _ = run_print_mode(
        container,
        PrintModeParams(prompt="hello", session_id="sess-1"),
        provider=provider,
    )
    second_exit_code, _ = run_print_mode(
        container,
        PrintModeParams(prompt="again", session_id="sess-1"),
        provider=provider,
    )

    assert first_exit_code == 0
    assert second_exit_code == 0
    assert len(provider.requests) == 2
    assert len(provider.requests[0].messages) == 1
    assert len(provider.requests[1].messages) == 3


def test_run_print_mode_can_resume_and_fork_session(tmp_path: Path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)
    provider = FakeProvider()

    first_exit_code, first_rendered = run_print_mode(
        container,
        PrintModeParams(
            prompt="hello",
            session_id="sess-1",
            output_format=OutputFormat.JSON,
        ),
        provider=provider,
    )
    second_exit_code, second_rendered = run_print_mode(
        container,
        PrintModeParams(
            prompt="branch",
            resume_session_id="sess-1",
            fork_session=True,
            output_format=OutputFormat.JSON,
        ),
        provider=provider,
    )

    first_payload = json.loads(first_rendered)
    second_payload = json.loads(second_rendered)

    assert first_exit_code == 0
    assert second_exit_code == 0
    assert first_payload["session_id"] == "sess-1"
    assert second_payload["session_id"] != "sess-1"
    assert second_payload["parent_session_id"] == "sess-1"
    assert len(provider.requests[1].messages) == 3
