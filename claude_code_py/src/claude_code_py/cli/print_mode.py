from pathlib import Path
from enum import StrEnum
import sys
from typing import Any, TextIO

from pydantic import BaseModel, Field

from claude_code_py.app.container import AppContainer
from claude_code_py.application.permission_service import PermissionService
from claude_code_py.application.query_service import QueryRequest, QueryService
from claude_code_py.application.session_service import SessionService
from claude_code_py.application.task_service import TaskService
from claude_code_py.common.json import to_json
from claude_code_py.common.text import normalize_text
from claude_code_py.domain.permissions import PermissionMode
from claude_code_py.providers.mcp import McpConnectionManager, load_mcp_server_configs
from claude_code_py.providers.llm.anthropic_provider import AnthropicLLMProvider
from claude_code_py.providers.llm.base import LLMConfigurationError, LLMProvider
from claude_code_py.providers.shell import SubprocessShellProvider
from claude_code_py.providers.storage import RuntimeStateStore
from claude_code_py.providers.storage.session_index import SqliteSessionIndex
from claude_code_py.providers.storage.transcript_store import JsonlTranscriptStore
from claude_code_py.session.recovery import RecoveryRequest
from claude_code_py.skills.loader import load_skills
from claude_code_py.tools import build_default_tool_registry
from claude_code_py.tools.base import ToolContext
from claude_code_py.tools.mcp import McpTool
from claude_code_py.application.tool_service import ToolService


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class PrintModeParams(BaseModel):
    prompt: str | None = None
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
    output_format: OutputFormat = OutputFormat.TEXT


def build_llm_provider(container: AppContainer) -> LLMProvider:
    return AnthropicLLMProvider.from_settings(container.settings)


def read_prompt_from_stdin(stdin: TextIO | None = None) -> str:
    stream = stdin or sys.stdin
    if stream.isatty():
        return ""
    try:
        return normalize_text(stream.read())
    except OSError:
        return ""


def merge_prompt_sources(cli_prompt: str | None, stdin_prompt: str | None) -> str:
    parts = [part for part in [cli_prompt, stdin_prompt] if part]
    return "\n".join(parts).strip()


def resolve_prompt(cli_prompt: str | None, stdin: TextIO | None = None) -> str:
    if cli_prompt:
        return normalize_text(cli_prompt)
    return read_prompt_from_stdin(stdin)


def build_system_prompt(
    system_prompt: str | None,
    system_prompt_file: Path | None,
    append_system_prompt: str | None,
) -> str | None:
    file_prompt: str | None = None
    if system_prompt_file is not None:
        file_prompt = system_prompt_file.read_text(encoding="utf-8")
    primary = system_prompt if system_prompt is not None else file_prompt
    if primary and append_system_prompt:
        return f"{primary}\n\n{append_system_prompt}"
    return primary or append_system_prompt


def run_print_mode(
    container: AppContainer,
    params: PrintModeParams,
    *,
    stdin: TextIO | None = None,
    provider: LLMProvider | None = None,
) -> tuple[int, str]:
    if params.system_prompt and params.system_prompt_file is not None:
        return 1, "Error: cannot use both --system-prompt and --system-prompt-file"

    prompt = resolve_prompt(params.prompt, stdin)
    if not prompt:
        return 1, "Error: prompt is required"

    try:
        llm_provider = provider or build_llm_provider(container)
    except LLMConfigurationError as exc:
        return 1, f"Error: {exc}"

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
        return 1, f"Error: {exc}"
    session_state = recovery.state

    tool_context = ToolContext(
        workspace_root=Path.cwd().resolve(),
        cwd=Path.cwd().resolve(),
        default_model=params.model or container.settings.default_model,
        llm_provider=llm_provider,
        shell_provider=SubprocessShellProvider(),
        metadata={"headless_mode": True},
    )
    try:
        mcp_server_configs = load_mcp_server_configs(
            tool_context.workspace_root,
            cli_configs=params.mcp_configs,
        )
    except ValueError as exc:
        return 1, f"Error: invalid MCP config: {exc}"
    mcp_manager = McpConnectionManager.connect_all(
        mcp_server_configs,
        workspace_root=tool_context.workspace_root,
    )
    mcp_tools = [
        McpTool(definition=definition, manager=mcp_manager)
        for definition in mcp_manager.list_tool_definitions()
    ]
    task_service = TaskService(allow_background=False)
    permission_service = PermissionService.from_sources(
        container=container,
        workspace_root=tool_context.workspace_root,
        mode=params.permission_mode,
        ask_mode_enabled=False,
        allow_rules=params.allow_rules,
        deny_rules=params.deny_rules,
        ask_rules=params.ask_rules,
    )
    tool_service = ToolService(
        build_default_tool_registry(
            extra_tools=[*mcp_tools],
        ),
        permission_service=permission_service,
    )
    task_service.configure(
        provider=llm_provider,
        tool_service=tool_service,
        tool_context=tool_context,
        default_max_tokens=container.settings.default_max_tokens,
    )
    tool_context.metadata["task_service"] = task_service
    tool_context.metadata["session_id"] = session_state.metadata.session_id
    tool_context.metadata["app_container"] = container
    tool_context.metadata["mcp_manager"] = mcp_manager
    tool_context.metadata["tool_registry"] = tool_service.registry
    tool_context.metadata["runtime_state_store"] = RuntimeStateStore(
        container.paths.data_dir / "runtime_state.json",
    )
    tool_context.metadata["loaded_skills"] = load_skills(tool_context.workspace_root)
    query_service = QueryService(
        llm_provider,
        tool_service=tool_service,
        tool_context=tool_context,
    )
    try:
        result = query_service.submit(
            QueryRequest(
                prompt=prompt,
                model=params.model or container.settings.default_model,
                history=session_state.messages,
                system_prompt=build_system_prompt(
                    params.system_prompt,
                    params.system_prompt_file,
                    params.append_system_prompt,
                ),
                max_tokens=container.settings.default_max_tokens,
            ),
        )
    except OSError as exc:
        return 1, f"Error: failed to read prompt file: {exc}"
    except RuntimeError as exc:
        return 1, f"Error: {exc}"
    finally:
        task_service.shutdown()
        mcp_manager.close()
    session_state = session_service.append_turn(session_state, result.new_messages)
    payload = result.model_dump(mode="json")
    payload["session_id"] = session_state.metadata.session_id
    payload["parent_session_id"] = session_state.metadata.parent_session_id
    payload["mcp_errors"] = mcp_manager.errors
    return 0, render_print_result(payload, params.output_format)


def render_print_result(result: dict[str, Any], output_format: OutputFormat) -> str:
    if output_format == OutputFormat.JSON:
        return to_json(result, indent=2)
    return str(result["text"])
