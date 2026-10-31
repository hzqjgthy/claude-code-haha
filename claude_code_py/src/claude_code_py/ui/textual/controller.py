from dataclasses import dataclass, field
from pathlib import Path
from threading import Event, Lock
from time import perf_counter

from claude_code_py.app.container import AppContainer
from claude_code_py.application.permission_service import PermissionService
from claude_code_py.application.query_service import QueryRequest, QueryService
from claude_code_py.application.session_service import SessionService
from claude_code_py.application.task_service import TaskService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.cli.print_mode import build_llm_provider, build_system_prompt
from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.commands import (
    CommandContext,
    build_command_registry,
    parse_slash_command,
)
from claude_code_py.commands.loader import build_plugin_commands
from claude_code_py.common.ids import new_permission_request_id
from claude_code_py.common.text import normalize_text
from claude_code_py.domain.permissions import (
    PermissionPromptChoice,
    PermissionPromptRequest,
)
from claude_code_py.providers.llm.base import LLMConfigurationError, LLMProvider
from claude_code_py.providers.mcp import McpConnectionManager, load_mcp_server_configs
from claude_code_py.providers.plugins import load_plugins
from claude_code_py.providers.remote import RemoteProvider, StatefulRemoteProvider
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
from claude_code_py.ui.state import (
    EditorDialogState,
    InfoDialogActionState,
    InfoDialogState,
    PermissionRequestState,
    PromptSuggestionState,
    StatusDetailState,
    StatusSnapshot,
    SelectorDialogState,
    SelectorOptionState,
    TranscriptEntry,
    TranscriptKind,
)


class _ControllerTerminalAdapter:
    def __init__(self) -> None:
        self.status: StatusSnapshot | None = None

    def bind_status(self, status) -> None:
        self.status = status


@dataclass(slots=True)
class _PendingPermissionWaiter:
    view: PermissionRequestState
    event: Event = field(default_factory=Event)
    response: PermissionPromptChoice | None = None


class TextualSessionController:
    def __init__(
        self,
        container: AppContainer,
        params: ReplModeParams,
        *,
        provider: LLMProvider | None = None,
        remote_provider: RemoteProvider | None = None,
    ) -> None:
        self._container = container
        self._params = params
        self._remote_provider = remote_provider or StatefulRemoteProvider(
            container.paths.data_dir / "remote_state.json"
        )
        self._bootstrap_entries: list[TranscriptEntry] = []
        self._transcript: list[TranscriptEntry] = []
        self._requested_editor_dialog: EditorDialogState | None = None
        self._requested_info_dialog: InfoDialogState | None = None
        self._requested_selector_dialog: SelectorDialogState | None = None
        self._permission_lock = Lock()
        self._permission_waiters: list[_PendingPermissionWaiter] = []
        self._shutdown_requested = False
        self._terminate_requested = False

        if params.system_prompt and params.system_prompt_file is not None:
            raise RuntimeError(
                "cannot use both --system-prompt and --system-prompt-file"
            )

        try:
            self._llm_provider = provider or build_llm_provider(container)
        except LLMConfigurationError as exc:
            raise RuntimeError(str(exc)) from exc

        self._session_service = SessionService(
            JsonlTranscriptStore(container.paths),
            SqliteSessionIndex(container.paths.session_index_path),
        )
        recovery = self._session_service.recover(
            RecoveryRequest(
                session_id=params.session_id,
                resume_session_id=params.resume_session_id,
                continue_latest=params.continue_session,
                fork_session=params.fork_session,
            ),
        )
        self._session_state = recovery.state
        self._model_name = params.model or container.settings.default_model
        self._tool_context = ToolContext(
            workspace_root=Path.cwd().resolve(),
            cwd=Path.cwd().resolve(),
            default_model=self._model_name,
            llm_provider=self._llm_provider,
            shell_provider=SubprocessShellProvider(),
            metadata={"headless_mode": False},
        )

        mcp_server_configs = load_mcp_server_configs(
            self._tool_context.workspace_root,
            cli_configs=params.mcp_configs,
        )
        self._mcp_manager = McpConnectionManager.connect_all(
            mcp_server_configs,
            workspace_root=self._tool_context.workspace_root,
        )
        self._mcp_tool_definitions = self._mcp_manager.list_tool_definitions()
        for error in self._mcp_manager.errors:
            self._bootstrap_entries.append(
                TranscriptEntry("system", f"MCP warning: {error}")
            )
        mcp_tools = [
            McpTool(definition=definition, manager=self._mcp_manager)
            for definition in self._mcp_tool_definitions
        ]

        self._task_service = TaskService(allow_background=True)
        self._permission_service = PermissionService.from_sources(
            container=container,
            workspace_root=self._tool_context.workspace_root,
            mode=params.permission_mode,
            ask_mode_enabled=True,
            allow_rules=params.allow_rules,
            deny_rules=params.deny_rules,
            ask_rules=params.ask_rules,
        )
        effective_permission_mode = self._permission_service.current_mode()
        self._tool_service = ToolService(
            build_default_tool_registry(extra_tools=[*mcp_tools]),
            permission_service=self._permission_service,
        )
        self._task_service.configure(
            provider=self._llm_provider,
            tool_service=self._tool_service,
            tool_context=self._tool_context,
            default_max_tokens=container.settings.default_max_tokens,
        )
        self._tool_context.metadata["task_service"] = self._task_service
        self._tool_context.metadata["session_id"] = (
            self._session_state.metadata.session_id
        )
        self._tool_context.metadata["permission_prompt_callback"] = (
            self._request_permission
        )

        self._query_service = QueryService(
            self._llm_provider,
            tool_service=self._tool_service,
            tool_context=self._tool_context,
        )
        self._system_prompt = build_system_prompt(
            params.system_prompt,
            params.system_prompt_file,
            params.append_system_prompt,
        )
        self._runtime_state_store = RuntimeStateStore(
            container.paths.data_dir / "runtime_state.json",
        )
        self._tool_context.metadata["runtime_state_store"] = self._runtime_state_store
        self._tool_context.metadata["app_container"] = container
        self._tool_context.metadata["mcp_manager"] = self._mcp_manager
        self._tool_context.metadata["tool_registry"] = self._tool_service.registry
        plugin_result = load_plugins(
            self._tool_context.workspace_root,
            extra_plugin_dirs=params.plugin_dirs,
        )
        self._plugins = plugin_result.plugins
        self._plugin_errors = plugin_result.errors
        for error in self._plugin_errors:
            self._bootstrap_entries.append(
                TranscriptEntry("system", f"Plugin warning: {error}")
            )
        self._skills = load_skills(
            self._tool_context.workspace_root,
            plugins=self._plugins,
        )
        self._tool_context.metadata["loaded_skills"] = self._skills
        self._remote_session_manager = RemoteSessionManager(
            session_service=self._session_service,
            provider=self._llm_provider,
            tool_service=self._tool_service,
            tool_context=self._tool_context,
            model_name=self._model_name,
            system_prompt=self._system_prompt,
            default_max_tokens=container.settings.default_max_tokens,
        )
        plugin_commands = build_plugin_commands(self._plugins)
        self._command_context = CommandContext(
            container=container,
            session_service=self._session_service,
            task_service=self._task_service,
            permission_service=self._permission_service,
            terminal=_ControllerTerminalAdapter(),
            workspace_root=self._tool_context.workspace_root,
            tool_context=self._tool_context,
            session_state=self._session_state,
            model_name=self._model_name,
            permission_mode=effective_permission_mode,
            base_system_prompt=self._system_prompt,
            plugin_dirs=params.plugin_dirs,
            plugins=self._plugins,
            plugin_errors=self._plugin_errors,
            skills=self._skills,
            mcp_server_configs=mcp_server_configs,
            mcp_tool_definitions=self._mcp_tool_definitions,
            mcp_manager=self._mcp_manager,
            remote_provider=self._remote_provider,
            remote_session_manager=self._remote_session_manager,
            runtime_state_store=self._runtime_state_store,
            command_registry=build_command_registry(
                self._skills,
                plugin_commands=plugin_commands,
            ),
        )

        self._transcript = [
            *self._bootstrap_entries,
            *self._render_existing_messages(),
        ]
        if recovery.source_summary is not None:
            action = "Forked from" if params.fork_session else "Resumed"
            self._transcript.append(
                TranscriptEntry(
                    "system",
                    f"{action} session {recovery.source_summary.session_id}",
                ),
            )

    @property
    def transcript(self) -> list[TranscriptEntry]:
        return list(self._transcript)

    @property
    def terminate_requested(self) -> bool:
        return self._terminate_requested

    def status_snapshot(self) -> StatusSnapshot:
        return StatusSnapshot(
            session_id=self._session_state.metadata.session_id,
            model=self._model_name,
            permission_mode=self._command_context.permission_mode,
            remote_status=self._remote_provider.status(),
        )

    def status_detail_snapshot(self) -> StatusDetailState:
        transcript = self._transcript
        return StatusDetailState(
            session_title=self._session_state.metadata.title,
            project_name=self._tool_context.workspace_root.name
            or str(self._tool_context.workspace_root),
            cwd_name=self._tool_context.cwd.name or str(self._tool_context.cwd),
            transcript_entries=len(transcript),
            user_entries=sum(1 for entry in transcript if entry.kind == "user"),
            assistant_entries=sum(
                1 for entry in transcript if entry.kind == "assistant"
            ),
            task_count=len(self._task_service.list_tasks()),
            command_count=len(self._command_context.command_registry.list_commands()),
            pending_permission_count=len(self._permission_waiters),
        )

    def task_summary_lines(self) -> list[str]:
        tasks = self._task_service.list_tasks()
        if not tasks:
            return ["No tasks"]

        lines = []
        for task in tasks[:10]:
            lines.append(
                f"{task.task_id[:8]} | "
                f"{task.kind} | "
                f"{task.status} | "
                f"bg={task.background} | "
                f"{task.description}",
            )
        return lines

    def task_detail_lines(self, task_id: str | None = None) -> list[str]:
        task = (
            self._task_service.get_task(task_id)
            if task_id is not None
            else (self._task_service.list_tasks() or [None])[0]
        )
        if task is None:
            return ["No task details available."]

        lines = [
            f"task_id: {task.task_id}",
            f"kind: {task.kind}",
            f"status: {task.status}",
            f"background: {task.background}",
            f"model: {task.model}",
            f"owner: {task.owner or '(none)'}",
            f"session_id: {task.session_id}",
            f"description: {task.description}",
            f"prompt: {task.prompt}",
        ]
        if task.metadata:
            lines.extend(["", "metadata:"])
            for key, value in sorted(task.metadata.items()):
                lines.append(f"{key}: {value}")
        if task.result_text:
            lines.extend(["", "result:", task.result_text])
        if task.error_message:
            lines.extend(["", "error:", task.error_message])
        return lines

    def command_help_lines(self) -> list[str]:
        lines = ["Available commands", ""]
        for command in self._command_context.command_registry.list_commands():
            if command.hidden:
                continue
            alias_suffix = (
                f" (aliases: {', '.join(command.spec.aliases)})"
                if command.spec.aliases
                else ""
            )
            lines.append(
                f"/{command.spec.name}{alias_suffix} - {command.spec.description}",
            )
            lines.append(f"usage: {command.usage}")
            lines.append(f"source: {command.source}")
            lines.append("")
        return lines[:-1] if lines[-1] == "" else lines

    def command_suggestions(
        self,
        prefix: str,
        *,
        limit: int | None = None,
    ) -> list[PromptSuggestionState]:
        normalized = prefix.strip().lower()
        suggestions: list[PromptSuggestionState] = []
        commands = self._command_context.command_registry.list_commands()
        if not normalized:
            priority = {
                "help": 0,
                "status": 1,
                "permissions": 2,
                "tasks": 3,
                "resume": 4,
                "model": 5,
            }
            commands = sorted(
                commands,
                key=lambda command: (
                    priority.get(command.spec.name, 99),
                    command.spec.name,
                ),
            )
        seen_values: set[str] = set()
        for command in commands:
            if command.hidden:
                continue
            names = (
                [command.spec.name]
                if not normalized
                else [command.spec.name, *command.spec.aliases]
            )
            for name in names:
                if normalized and not name.startswith(normalized):
                    continue
                value = f"/{name}"
                if value in seen_values:
                    continue
                seen_values.add(value)
                description = command.spec.description
                if name != command.spec.name:
                    description = (
                        f"{description} (alias for /{command.spec.name})"
                    )
                suggestions.append(
                    PromptSuggestionState(
                        value=value,
                        description=description,
                        source=command.source,
                    )
                )
                if limit is not None and len(suggestions) >= limit:
                    return suggestions
        return suggestions

    def permission_summary_lines(self) -> list[str]:
        rules = self._permission_service.list_rules()
        lines = [
            f"permission_mode: {self._command_context.permission_mode}",
            "interactive_ask_ui: enabled",
            f"rule_count: {len(rules)}",
        ]
        for behavior in ("allow", "deny", "ask"):
            rendered = [
                _format_permission_rule(rule)
                for rule in rules
                if rule.behavior == behavior
            ]
            lines.append(f"{behavior}_rules: {', '.join(rendered[:5]) or '(none)'}")
        remote = self._remote_provider.status()
        lines.append(
            "remote_status: "
            f"{remote.mode} / {'connected' if remote.connected else 'disconnected'}",
        )
        if remote.detail:
            lines.append(f"remote_detail: {remote.detail}")
        if remote.session_url:
            lines.append(f"remote_session_url: {remote.session_url}")
        return lines

    def remote_summary_lines(self) -> list[str]:
        remote = self._remote_provider.status()
        lines = [
            f"mode: {remote.mode}",
            f"connected: {remote.connected}",
            f"transport: {remote.transport}",
            f"remote_session_id: {remote.remote_session_id or '(none)'}",
            f"detail: {remote.detail or '(none)'}",
            f"session_url: {remote.session_url or '(none)'}",
            "last_heartbeat: "
            f"{remote.last_heartbeat_at.isoformat(timespec='seconds') if remote.last_heartbeat_at else '(none)'}",
        ]
        return lines

    def footer_lines(self) -> list[str]:
        return [
            "Enter submit  |  F2 policy  |  F3 latest task  |  F4 remote  |  F5 refresh  |  q quit",
            "/help /status /memory /sessions /share /rewind",
        ]

    def pending_permission_request(self) -> PermissionRequestState | None:
        with self._permission_lock:
            if not self._permission_waiters:
                return None
            return self._permission_waiters[0].view

    def resolve_permission_request(self, choice: PermissionPromptChoice) -> bool:
        with self._permission_lock:
            if not self._permission_waiters:
                return False
            waiter = self._permission_waiters.pop(0)
            waiter.response = choice
            waiter.event.set()

        label = {
            "allow_once": "Approved once",
            "allow_session": "Approved for session",
            "allow_project": "Approved for project",
            "deny_once": "Denied once",
            "deny_session": "Denied for session",
            "deny_project": "Denied for project",
        }[choice]
        kind: TranscriptKind = "system" if choice.startswith("allow") else "error"
        self._transcript.append(
            TranscriptEntry(
                kind,
                f"{label}: {waiter.view.tool_name} ({waiter.view.summary})",
            ),
        )
        return True

    def submit_prompt(self, prompt: str) -> list[TranscriptEntry]:
        normalized_prompt = normalize_text(prompt)
        if not normalized_prompt:
            return []

        entries: list[TranscriptEntry] = [TranscriptEntry("user", normalized_prompt)]
        command_result = None
        invocation = parse_slash_command(normalized_prompt)
        if invocation is not None:
            command_result = self._command_context.command_registry.execute(
                self._command_context,
                invocation,
            )
            self._session_state = self._command_context.session_state
            self._model_name = self._command_context.model_name
            self._tool_context.metadata["session_id"] = (
                self._session_state.metadata.session_id
            )
            if command_result.refresh_transcript:
                self._reset_transcript_from_session()
            if (
                command_result.dialog_title is not None
                and command_result.dialog_lines is not None
            ):
                self._requested_info_dialog = InfoDialogState(
                    kind=command_result.dialog_kind or f"command:{invocation.name}",
                    title=command_result.dialog_title,
                    lines=command_result.dialog_lines,
                    actions=[
                        InfoDialogActionState(
                            label=action.label,
                            command=action.command,
                            description=action.description,
                        )
                        for action in (command_result.dialog_actions or [])
                    ],
                )
            if (
                command_result.selector_title is not None
                and command_result.selector_options is not None
            ):
                self._requested_selector_dialog = SelectorDialogState(
                    kind=command_result.selector_kind or f"selector:{invocation.name}",
                    title=command_result.selector_title,
                    options=[
                        SelectorOptionState(
                            label=option.label,
                            command=option.command,
                            description=option.description,
                            preview_lines=list(option.preview_lines or []),
                        )
                        for option in command_result.selector_options
                    ],
                )
            if (
                command_result.editor_title is not None
                and command_result.editor_path is not None
                and command_result.editor_text is not None
            ):
                self._requested_editor_dialog = EditorDialogState(
                    kind=command_result.editor_kind or f"editor:{invocation.name}",
                    title=command_result.editor_title,
                    file_path=command_result.editor_path,
                    text=command_result.editor_text,
                    language=command_result.editor_language or "markdown",
                )
            if command_result.kind == "message":
                entries = [TranscriptEntry("system", command_result.message or "")]
                self._transcript.extend(entries)
                if command_result.terminate_session:
                    self._terminate_requested = True
                return entries
            if command_result.kind == "error":
                entries = [
                    TranscriptEntry(
                        "error", command_result.message or "Command failed."
                    )
                ]
                self._transcript.extend(entries)
                return entries
            if command_result.kind == "noop":
                return []
            if command_result.kind == "prompt":
                normalized_prompt = command_result.prompt or ""
                if not normalized_prompt:
                    return []

        started_at = perf_counter()
        result = self._query_service.submit(
            QueryRequest(
                prompt=normalized_prompt,
                model=self._model_name,
                history=self._session_state.messages,
                system_prompt=(
                    command_result.transient_system_prompt
                    if command_result is not None
                    and command_result.transient_system_prompt is not None
                    else self._system_prompt
                ),
                max_tokens=self._container.settings.default_max_tokens,
            ),
        )
        self._runtime_state_store.record_session_usage(
            self._session_state.metadata.session_id,
            model=self._model_name,
            raw_response=result.raw_response,
            duration_ms=int((perf_counter() - started_at) * 1000),
        )
        self._session_state = self._session_service.append_turn(
            self._session_state,
            result.new_messages,
        )
        self._command_context.session_state = self._session_state
        self._command_context.model_name = self._model_name
        self._tool_context.metadata["session_id"] = (
            self._session_state.metadata.session_id
        )
        entries.append(TranscriptEntry("assistant", result.text))
        self._transcript.extend(entries)
        return entries

    def drain_background_events(self) -> list[TranscriptEntry]:
        events = self._task_service.drain_events()
        entries = [TranscriptEntry("system", event.message) for event in events]
        self._transcript.extend(entries)
        return entries

    def append_ui_entry(self, kind: TranscriptKind, text: str) -> TranscriptEntry:
        entry = TranscriptEntry(kind, text)
        self._transcript.append(entry)
        return entry

    def consume_requested_info_dialog(self) -> InfoDialogState | None:
        dialog = self._requested_info_dialog
        self._requested_info_dialog = None
        return dialog

    def consume_requested_editor_dialog(self) -> EditorDialogState | None:
        dialog = self._requested_editor_dialog
        self._requested_editor_dialog = None
        return dialog

    def consume_requested_selector_dialog(self) -> SelectorDialogState | None:
        dialog = self._requested_selector_dialog
        self._requested_selector_dialog = None
        return dialog

    def shutdown(self) -> None:
        self._shutdown_requested = True
        with self._permission_lock:
            waiters = list(self._permission_waiters)
            self._permission_waiters.clear()
        for waiter in waiters:
            waiter.response = "deny_once"
            waiter.event.set()
        self._task_service.shutdown()
        self._mcp_manager.close()

    def _reset_transcript_from_session(self) -> None:
        self._transcript = [
            *self._bootstrap_entries,
            *self._render_existing_messages(),
        ]

    def _request_permission(
        self,
        request: PermissionPromptRequest,
    ) -> PermissionPromptChoice:
        if self._shutdown_requested:
            return "deny_once"

        waiter = _PendingPermissionWaiter(
            view=PermissionRequestState(
                request_id=new_permission_request_id(),
                tool_name=request.tool_name,
                summary=request.summary,
                request_kind=request.request_kind,
                title=request.title,
                subtitle=request.subtitle,
                prompt=request.prompt,
                reason=request.reason,
                target_lines=self._format_permission_targets(request),
                detail_lines=list(request.detail_lines),
                preview=request.preview,
            ),
        )
        with self._permission_lock:
            self._permission_waiters.append(waiter)

        self._transcript.append(
            TranscriptEntry(
                "system",
                f"Permission requested: {request.tool_name} ({request.summary})",
            ),
        )
        waiter.event.wait()
        return waiter.response or "deny_once"

    def _render_existing_messages(self) -> list[TranscriptEntry]:
        entries: list[TranscriptEntry] = []
        for message in self._session_state.messages:
            if message.kind == "user":
                entries.append(TranscriptEntry("user", message.content))
            elif message.kind == "assistant":
                entries.append(TranscriptEntry("assistant", message.content))
            elif message.kind == "tool_use":
                entries.append(
                    TranscriptEntry(
                        "system",
                        f"Tool call: {message.tool_name} {message.arguments}",
                    ),
                )
            elif message.kind == "tool_result":
                kind: TranscriptKind = "error" if message.is_error else "system"
                entries.append(
                    TranscriptEntry(
                        kind,
                        f"Tool result: {message.tool_name}\n{message.output}",
                    ),
                )
        return entries

    @staticmethod
    def _format_permission_targets(request: PermissionPromptRequest) -> list[str]:
        lines: list[str] = []
        for target in request.targets:
            if target.kind and target.value:
                lines.append(f"{target.tool_name}({target.kind}:{target.value})")
        if not lines:
            lines.append(request.tool_name)
        return lines


def _format_permission_rule(rule) -> str:
    if rule.kind is None:
        return rule.tool_name
    return f"{rule.tool_name}({rule.kind}:{rule.pattern})"
