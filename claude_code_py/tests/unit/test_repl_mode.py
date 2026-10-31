from dataclasses import dataclass, field
from pathlib import Path

from claude_code_py.cli.repl_mode import ReplModeParams, run_repl_mode
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


@dataclass
class FakeTerminal:
    prompts: list[object]
    systems: list[str] = field(default_factory=list)
    assistants: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    interrupts: int = 0
    greeted: bool = False
    exited: bool = False
    status: object | None = None

    def bind_status(self, status) -> None:
        self.status = status

    def show_welcome(self) -> None:
        self.greeted = True

    def show_system(self, text: str) -> None:
        self.systems.append(text)

    def show_assistant(self, text: str) -> None:
        self.assistants.append(text)

    def show_error(self, text: str) -> None:
        self.errors.append(text)

    def show_interrupt(self) -> None:
        self.interrupts += 1

    def show_goodbye(self) -> None:
        self.exited = True

    def read_prompt(self) -> str | None:
        if not self.prompts:
            return None
        value = self.prompts.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def test_run_repl_mode_supports_multi_turn_history(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    terminal = FakeTerminal(prompts=["hello", "again", None])
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    exit_code = run_repl_mode(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
        terminal=terminal,
    )

    assert exit_code == 0
    assert terminal.greeted is True
    assert terminal.exited is True
    assert terminal.assistants == ["assistant:hello", "assistant:again"]
    assert len(provider.requests) == 2
    assert len(provider.requests[0].messages) == 1
    assert len(provider.requests[1].messages) == 3


def test_run_repl_mode_handles_resume_and_fork(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    first_terminal = FakeTerminal(prompts=["hello", None])
    run_repl_mode(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
        terminal=first_terminal,
    )

    fork_terminal = FakeTerminal(prompts=["branch", None])
    exit_code = run_repl_mode(
        container,
        ReplModeParams(resume_session_id="sess-1", fork_session=True),
        provider=provider,
        terminal=fork_terminal,
    )

    assert exit_code == 0
    assert any("Forked from session sess-1" == item for item in fork_terminal.systems)


def test_run_repl_mode_reports_interrupts_without_losing_loop(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    terminal = FakeTerminal(prompts=[KeyboardInterrupt(), "hello", None])
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    exit_code = run_repl_mode(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
        terminal=terminal,
    )

    assert exit_code == 0
    assert terminal.interrupts == 1
    assert terminal.assistants == ["assistant:hello"]


def test_run_repl_mode_supports_slash_model_and_review(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    terminal = FakeTerminal(prompts=["/model my-model", "/review auth changes", None])
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    exit_code = run_repl_mode(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
        terminal=terminal,
    )

    assert exit_code == 0
    assert "Model updated to my-model" in terminal.systems
    assert len(provider.requests) == 1
    assert provider.requests[0].model == "my-model"
    assert "Additional context:\nauth changes" in provider.requests[0].messages[-1].content


def test_run_repl_mode_exit_alias_terminates_session(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    terminal = FakeTerminal(prompts=["/quit"])
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)

    exit_code = run_repl_mode(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
        terminal=terminal,
    )

    assert exit_code == 0
    assert any("Goodbye!" in message for message in terminal.systems)
    assert provider.requests == []


def test_run_repl_mode_supports_invocable_skill_commands(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    terminal = FakeTerminal(prompts=["/reviewer inspect auth", None])
    workspace_root = container.paths.root / "workspace"
    skill_dir = workspace_root / ".claude" / "skills" / "reviewer"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        (
            "---\n"
            "name: Reviewer\n"
            "description: Review code changes\n"
            "user-invocable: true\n"
            "argument-hint: [scope]\n"
            "---\n"
            "Focus on regressions and missing tests."
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace_root)

    exit_code = run_repl_mode(
        container,
        ReplModeParams(session_id="sess-1"),
        provider=provider,
        terminal=terminal,
    )

    assert exit_code == 0
    assert len(provider.requests) == 1
    assert provider.requests[0].messages[-1].content == "inspect auth"
    assert "Focus on regressions and missing tests." in (
        provider.requests[0].system_prompt or ""
    )


def test_run_repl_mode_supports_plugin_commands_and_skills(tmp_path, monkeypatch) -> None:
    container = make_test_container(tmp_path)
    provider = FakeProvider()
    terminal = FakeTerminal(prompts=["/shipit release notes", "/plugin-review auth", None])
    workspace_root = container.paths.root / "workspace"
    plugin_root = tmp_path / "demo-plugin"
    command_dir = plugin_root / "commands"
    skill_dir = plugin_root / "skills"
    workspace_root.mkdir(parents=True, exist_ok=True)
    command_dir.mkdir(parents=True, exist_ok=True)
    skill_dir.mkdir(parents=True, exist_ok=True)
    (plugin_root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin_root / ".claude-plugin" / "plugin.json").write_text(
        (
            '{'
            '"name":"demo-plugin",'
            '"commands":["./commands"],'
            '"skills":["./skills"]'
            '}'
        ),
        encoding="utf-8",
    )
    (command_dir / "shipit.md").write_text(
        (
            "---\n"
            "name: ShipIt\n"
            "description: Prepare a release summary\n"
            "argument-hint: [scope]\n"
            "---\n"
            "Prepare the requested release summary."
        ),
        encoding="utf-8",
    )
    (skill_dir / "plugin-review.md").write_text(
        (
            "---\n"
            "name: Plugin Review\n"
            "description: Review changes from plugin skill\n"
            "user-invocable: true\n"
            "---\n"
            "Review the selected scope carefully."
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace_root)

    exit_code = run_repl_mode(
        container,
        ReplModeParams(
            session_id="sess-1",
            plugin_dirs=[str(plugin_root)],
        ),
        provider=provider,
        terminal=terminal,
    )

    assert exit_code == 0
    assert len(provider.requests) == 2
    assert provider.requests[0].messages[-1].content == "release notes"
    assert "Prepare the requested release summary." in (
        provider.requests[0].system_prompt or ""
    )
    assert provider.requests[1].messages[-1].content == "auth"
    assert "Review the selected scope carefully." in (
        provider.requests[1].system_prompt or ""
    )
