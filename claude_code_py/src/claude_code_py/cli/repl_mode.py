from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, Field

from claude_code_py.app.container import AppContainer
from claude_code_py.application.task_service import TaskService
from claude_code_py.commands import (
    CommandContext,
    build_command_registry,
    parse_slash_command,
)
from claude_code_py.commands.loader import build_plugin_commands
from claude_code_py.application.permission_service import PermissionService
from claude_code_py.application.query_service import QueryRequest, QueryService
from claude_code_py.application.session_service import SessionService
from claude_code_py.cli.print_mode import build_llm_provider, build_system_prompt
from claude_code_py.common.text import normalize_text
from claude_code_py.domain.permissions import PermissionMode
from claude_code_py.providers.mcp import McpConnectionManager, load_mcp_server_configs
from claude_code_py.providers.plugins import load_plugins
from claude_code_py.providers.llm.base import LLMConfigurationError, LLMProvider
from claude_code_py.providers.remote import StatefulRemoteProvider
from claude_code_py.providers.remote.session_manager import RemoteSessionManager
from claude_code_py.providers.shell import SubprocessShellProvider
from claude_code_py.providers.storage import RuntimeStateStore
from claude_code_py.providers.storage.session_index import SqliteSessionIndex
from claude_code_py.providers.storage.transcript_store import JsonlTranscriptStore
from claude_code_py.session.recovery import RecoveryRequest
from claude_code_py.skills.loader import load_skills
from claude_code_py.tools import build_default_tool_registry
from claude_code_py.tools.base import ToolContext
from claude_code_py.tools.mcp import McpTool
from claude_code_py.ui.prompt_toolkit import PromptToolkitReplTerminal, ReplStatus
from claude_code_py.application.tool_service import ToolService


class ReplModeParams(BaseModel):
    initial_prompt: str | None = None
    session_id: str | None = None
    resume_session_id: str | None = None
    continue_session: bool = False
    fork_session: bool = False
    mcp_configs: list[str] = Field(default_factory=list)
    plugin_dirs: list[str] = Field(default_factory=list)
    model: str | None = None
    permission_mode: PermissionMode = "default"
    allow_rules: list[str] = Field(default_factory=list)
    deny_rules: list[str] = Field(default_factory=list)
    ask_rules: list[str] = Field(default_factory=list)
    system_prompt: str | None = None
    system_prompt_file: Path | None = None
    append_system_prompt: str | None = None


def run_repl_mode(
    container: AppContainer,
    params: ReplModeParams,
    *,
    provider: LLMProvider | None = None,
    terminal: PromptToolkitReplTerminal | None = None,
) -> int:
    if params.system_prompt and params.system_prompt_file is not None:
        _show_error(
            terminal,
            "cannot use both --system-prompt and --system-prompt-file",
        )
        return 1

    try:
        llm_provider = provider or build_llm_provider(container)
    except LLMConfigurationError as exc:
        _show_error(terminal, str(exc))
        return 1

    session_service = SessionService(
        JsonlTranscriptStore(container.paths),
        SqliteSessionIndex(container.paths.session_index_path),
    )
    try:
        recovery = session_service.recover(
            RecoveryRequest(
                session_id=params.session_id,
                resume_session_id=params.resume_session_id,
                continue_latest=params.continue_session,
                fork_session=params.fork_session,
            ),
        )
    except (RuntimeError, ValueError) as exc:
        _show_error(terminal, str(exc))
        return 1

    try:
        repl_terminal = terminal or PromptToolkitReplTerminal(
            data_dir=container.paths.data_dir,
        )
    except RuntimeError:
        raise

    model_name = params.model or container.settings.default_model
    tool_context = ToolContext(
        workspace_root=Path.cwd().resolve(),
        cwd=Path.cwd().resolve(),
        default_model=model_name,
        llm_provider=llm_provider,
        shell_provider=SubprocessShellProvider(),
        metadata={"headless_mode": False},
    )
    try:
        mcp_server_configs = load_mcp_server_configs(
            tool_context.workspace_root,
            cli_configs=params.mcp_configs,
        )
    except ValueError as exc:
        repl_terminal.show_error(f"invalid MCP config: {exc}")
        return 1
    mcp_manager = McpConnectionManager.connect_all(
        mcp_server_configs,
        workspace_root=tool_context.workspace_root,
    )
    mcp_tool_definitions = mcp_manager.list_tool_definitions()
    mcp_tools = [
        McpTool(definition=definition, manager=mcp_manager)
        for definition in mcp_tool_definitions
    ]
    for error in mcp_manager.errors:
        repl_terminal.show_system(f"MCP warning: {error}")
    task_service = TaskService(allow_background=True)
    permission_service = PermissionService.from_sources(
        container=container,
        workspace_root=tool_context.workspace_root,
        mode=params.permission_mode,
        ask_mode_enabled=False,
        allow_rules=params.allow_rules,
        deny_rules=params.deny_rules,
        ask_rules=params.ask_rules,
    )
    effective_permission_mode = permission_service.current_mode()
    repl_terminal.bind_status(
        ReplStatus(
            session_id=recovery.state.metadata.session_id,
            model=model_name,
            permission_mode=effective_permission_mode,
        ),
    )
    repl_terminal.show_welcome()
    if recovery.source_summary is not None:
        action = "Forked from" if params.fork_session else "Resumed"
        repl_terminal.show_system(f"{action} session {recovery.source_summary.session_id}")
    tool_service = ToolService(
        build_default_tool_registry(extra_tools=[*mcp_tools]),
        permission_service=permission_service,
    )
    task_service.configure(
        provider=llm_provider,
        tool_service=tool_service,
        tool_context=tool_context,
        default_max_tokens=container.settings.default_max_tokens,
    )
    query_service = QueryService(
        llm_provider,
        tool_service=tool_service,
        tool_context=tool_context,
    )
    session_state = recovery.state
    tool_context.metadata["task_service"] = task_service
    tool_context.metadata["session_id"] = session_state.metadata.session_id
    system_prompt = build_system_prompt(
        params.system_prompt,
        params.system_prompt_file,
        params.append_system_prompt,
    )
    plugin_result = load_plugins(
        tool_context.workspace_root,
        extra_plugin_dirs=params.plugin_dirs,
    )
    for error in plugin_result.errors:
        repl_terminal.show_system(f"Plugin warning: {error}")
    loaded_skills = load_skills(
        tool_context.workspace_root,
        plugins=plugin_result.plugins,
    )
    plugin_commands = build_plugin_commands(plugin_result.plugins)
    runtime_state_store = RuntimeStateStore(
        container.paths.data_dir / "runtime_state.json",
    )
    tool_context.metadata["task_service"] = task_service
    tool_context.metadata["session_id"] = session_state.metadata.session_id
    tool_context.metadata["runtime_state_store"] = runtime_state_store
    tool_context.metadata["app_container"] = container
    tool_context.metadata["mcp_manager"] = mcp_manager
    tool_context.metadata["tool_registry"] = tool_service.registry
    tool_context.metadata["loaded_skills"] = loaded_skills
    remote_provider = StatefulRemoteProvider(
        container.paths.data_dir / "remote_state.json"
    )
    remote_session_manager = RemoteSessionManager(
        session_service=session_service,
        provider=llm_provider,
        tool_service=tool_service,
        tool_context=tool_context,
        model_name=model_name,
        system_prompt=system_prompt,
        default_max_tokens=container.settings.default_max_tokens,
    )
    command_context = CommandContext(
        container=container,
        session_service=session_service,
        task_service=task_service,
        permission_service=permission_service,
        terminal=repl_terminal,
        workspace_root=tool_context.workspace_root,
        tool_context=tool_context,
        session_state=session_state,
        model_name=model_name,
        permission_mode=effective_permission_mode,
        base_system_prompt=system_prompt,
        plugin_dirs=params.plugin_dirs,
        plugins=plugin_result.plugins,
        plugin_errors=plugin_result.errors,
        skills=loaded_skills,
        mcp_server_configs=mcp_server_configs,
        mcp_tool_definitions=mcp_tool_definitions,
        mcp_manager=mcp_manager,
        remote_provider=remote_provider,
        remote_session_manager=remote_session_manager,
        runtime_state_store=runtime_state_store,
        command_registry=build_command_registry(
            loaded_skills,
            plugin_commands=plugin_commands,
        ),
    )

    def ask_user_callback(payload: dict[str, object]) -> dict[str, str]:
        questions = payload.get("questions")
        if not isinstance(questions, list):
            raise RuntimeError("Invalid AskUserQuestion payload.")
        answers: dict[str, str] = {}
        for item in questions:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            header = str(item.get("header") or "Question").strip()
            options = item.get("options")
            if not question or not isinstance(options, list) or len(options) < 2:
                continue
            repl_terminal.show_system(f"[{header}] {question}")
            for index, option in enumerate(options, start=1):
                if not isinstance(option, dict):
                    continue
                label = str(option.get("label") or f"Option {index}")
                description = str(option.get("description") or "")
                suffix = f" - {description}" if description else ""
                repl_terminal.show_system(f"  {index}. {label}{suffix}")
            response = repl_terminal.read_prompt()
            if response is None:
                raise RuntimeError("User declined to answer AskUserQuestion.")
            raw_answer = response.strip()
            selected = raw_answer
            if raw_answer.isdigit():
                index = int(raw_answer) - 1
                if 0 <= index < len(options) and isinstance(options[index], dict):
                    selected = str(options[index].get("label") or raw_answer)
            answers[question] = selected
        return answers

    tool_context.metadata["ask_user_callback"] = ask_user_callback

    pending_prompt = params.initial_prompt
    try:
        while True:
            for event in task_service.drain_events():
                repl_terminal.show_system(event.message)
            try:
                prompt = pending_prompt if pending_prompt is not None else repl_terminal.read_prompt()
            except KeyboardInterrupt:
                repl_terminal.show_interrupt()
                pending_prompt = None
                continue

            pending_prompt = None
            if prompt is None:
                repl_terminal.show_goodbye()
                return 0

            normalized_prompt = normalize_text(prompt)
            if not normalized_prompt:
                continue

            command_result = None
            invocation = parse_slash_command(normalized_prompt)
            if invocation is not None:
                command_result = command_context.command_registry.execute(
                    command_context,
                    invocation,
                )
                session_state = command_context.session_state
                model_name = command_context.model_name
                tool_context.metadata["session_id"] = session_state.metadata.session_id
                if command_result.kind == "message":
                    repl_terminal.show_system(command_result.message or "")
                    if command_result.terminate_session:
                        return 0
                    continue
                if command_result.kind == "error":
                    repl_terminal.show_error(command_result.message or "Command failed.")
                    continue
                if command_result.kind == "noop":
                    continue
                if command_result.kind == "prompt":
                    normalized_prompt = command_result.prompt or ""
                    if not normalized_prompt:
                        continue

            try:
                started_at = perf_counter()
                result = query_service.submit(
                    QueryRequest(
                        prompt=normalized_prompt,
                        model=model_name,
                        history=session_state.messages,
                        system_prompt=(
                            command_result.transient_system_prompt
                            if command_result is not None
                            and command_result.transient_system_prompt is not None
                            else system_prompt
                        ),
                        max_tokens=container.settings.default_max_tokens,
                    ),
                )
            except KeyboardInterrupt:
                repl_terminal.show_interrupt()
                continue
            except (OSError, RuntimeError) as exc:
                repl_terminal.show_error(str(exc))
                continue
            runtime_state_store.record_session_usage(
                session_state.metadata.session_id,
                model=model_name,
                raw_response=result.raw_response,
                duration_ms=int((perf_counter() - started_at) * 1000),
            )

            session_state = session_service.append_turn(session_state, result.new_messages)
            command_context.session_state = session_state
            command_context.model_name = model_name
            tool_context.metadata["session_id"] = session_state.metadata.session_id
            repl_terminal.show_assistant(result.text)
    finally:
        task_service.shutdown()
        mcp_manager.close()


def _show_error(terminal: PromptToolkitReplTerminal | None, message: str) -> None:
    if terminal is not None:
        terminal.show_error(message)
        return
    print(f"[error] {message}", flush=True)
