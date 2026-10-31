from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import shlex
import subprocess
import sys
from threading import Event, Lock, Thread
from time import perf_counter
from urllib.parse import urlparse

from claude_code_py.application.permission_service import PermissionService
from claude_code_py.application.query_service import QueryRequest, QueryService
from claude_code_py.application.session_service import SessionService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.common.ids import new_permission_request_id, new_task_id
from claude_code_py.domain.messages import (
    Message,
    deserialize_message,
)
from claude_code_py.domain.permissions import (
    PermissionPromptChoice,
    PermissionPromptRequest,
)
from claude_code_py.domain.tasks import TaskRecord
from claude_code_py.providers.llm.base import LLMProvider
from claude_code_py.providers.remote.websocket_transport import (
    WebSocketTextStream,
    WebSocketTransportError,
    connect_websocket,
)
from claude_code_py.permissions.rules import render_rule
from claude_code_py.tools.base import ToolContext


@dataclass(slots=True)
class RemotePermissionRequestState:
    request_id: str
    prompt: PermissionPromptRequest
    event: Event = field(default_factory=Event)
    response: PermissionPromptChoice | None = None


class RemoteSessionManager:
    def __init__(
        self,
        *,
        session_service: SessionService,
        provider: LLMProvider,
        tool_service: ToolService,
        tool_context: ToolContext,
        model_name: str,
        system_prompt: str | None,
        default_max_tokens: int,
        permission_service: PermissionService | None = None,
    ) -> None:
        self._session_service = session_service
        self._provider = provider
        self._tool_service = tool_service
        self._tool_context = tool_context
        self._model_name = model_name
        self._system_prompt = system_prompt
        self._default_max_tokens = default_max_tokens
        self._permission_service = permission_service
        self._lock = Lock()
        self._transport_lock = Lock()
        self._state = None
        self._pending_permissions: list[RemotePermissionRequestState] = []
        self._active_task: TaskRecord | None = None
        self._worker: Thread | None = None
        self._task_done = Event()
        self._transport_mode = "in_process"
        self._process: subprocess.Popen[str] | None = None
        self._process_reader: Thread | None = None
        self._process_stderr_reader: Thread | None = None
        self._websocket: WebSocketTextStream | None = None
        self._websocket_reader: Thread | None = None
        self._last_remote_session_id: str | None = None
        self._last_local_session_id: str | None = None
        self._last_session_url: str | None = None
        self._last_ssh_host: str | None = None
        self._last_ssh_remote_cwd: str | None = None
        self._last_requested_transport: str = "in_process"
        self._cancelled_task_ids: set[str] = set()
        self._event_log: list[str] = []

    def connect(
        self,
        *,
        remote_session_id: str,
        local_session_id: str,
        transport_mode: str = "in_process",
        session_url: str | None = None,
        ssh_host: str | None = None,
        ssh_remote_cwd: str | None = None,
    ) -> str:
        with self._lock:
            self._state = self._session_service.load_or_create(remote_session_id)
            self._tool_context.metadata["remote_local_session_id"] = local_session_id
            self._tool_context.metadata["remote_session_id"] = remote_session_id
            self._last_remote_session_id = remote_session_id
            self._last_local_session_id = local_session_id
            self._last_session_url = session_url
            self._last_ssh_host = ssh_host
            self._last_ssh_remote_cwd = ssh_remote_cwd
            self._last_requested_transport = transport_mode

        if transport_mode != self._transport_mode:
            self.disconnect_transport()

        actual_transport = transport_mode
        if transport_mode == "websocket":
            if session_url is None:
                raise RuntimeError("WebSocket direct-connect requires a session URL.")
            try:
                self._connect_websocket(session_url)
            except Exception as exc:
                self._append_event(
                    f"websocket connect failed ({exc}); falling back to local subprocess transport"
                )
                self._spawn_subprocess_worker(
                    remote_session_id=remote_session_id,
                    local_session_id=local_session_id,
                )
                actual_transport = "subprocess"
        elif transport_mode == "subprocess":
            self._spawn_subprocess_worker(
                remote_session_id=remote_session_id,
                local_session_id=local_session_id,
            )
        elif transport_mode == "ssh":
            if ssh_host is None:
                raise RuntimeError("SSH transport requires a host.")
            self._spawn_ssh_worker(
                remote_session_id=remote_session_id,
                local_session_id=local_session_id,
                ssh_host=ssh_host,
                ssh_remote_cwd=ssh_remote_cwd,
            )
        else:
            self._append_event(f"connected transport={transport_mode}")

        self._transport_mode = actual_transport
        return actual_transport

    def remote_session_id(self) -> str | None:
        with self._lock:
            return self._state.metadata.session_id if self._state is not None else None

    def submit_prompt(self, prompt: str) -> TaskRecord:
        with self._lock:
            if self._state is None:
                raise RuntimeError("Remote session is not connected.")
            if self._active_task is not None and self._active_task.status in {"pending", "running"}:
                raise RuntimeError("Remote session is already processing another prompt.")
            task = TaskRecord(
                task_id=new_task_id(),
                kind="agent",
                description=f"remote:{prompt[:48]}",
                prompt=prompt,
                status="pending",
                background=True,
                model=self._model_name,
                owner="remote-session",
                session_id=self._state.metadata.session_id,
            )
            self._active_task = task
            self._task_done.clear()
            self._cancelled_task_ids.discard(task.task_id)

        self._append_event(f"submit_prompt task_id={task.task_id}")
        if self._transport_mode in {"subprocess", "websocket", "ssh"}:
            self._send_transport_message(
                {
                    "type": "submit_prompt",
                    "task_id": task.task_id,
                    "prompt": prompt,
                }
            )
        else:
            self._worker = Thread(
                target=self._run_prompt,
                args=(task.task_id, prompt),
                daemon=True,
            )
            self._worker.start()
        return task.model_copy(deep=True)

    def current_task(self) -> TaskRecord | None:
        with self._lock:
            return self._active_task.model_copy(deep=True) if self._active_task is not None else None

    def wait(self, timeout: float | None = None) -> TaskRecord | None:
        if self._transport_mode in {"subprocess", "websocket", "ssh"}:
            self._task_done.wait(timeout=timeout)
        else:
            worker = self._worker
            if worker is not None:
                worker.join(timeout=timeout)
        return self.current_task()

    def messages(self) -> list[Message]:
        with self._lock:
            if self._state is None:
                return []
            return list(self._state.messages)

    def events(self) -> list[str]:
        with self._lock:
            return list(self._event_log)

    def pending_permission_requests(self) -> list[RemotePermissionRequestState]:
        with self._lock:
            return [
                RemotePermissionRequestState(
                    request_id=item.request_id,
                    prompt=item.prompt.model_copy(deep=True),
                    response=item.response,
                )
                for item in self._pending_permissions
            ]

    def resolve_permission_request(
        self,
        request_id: str,
        choice: PermissionPromptChoice,
    ) -> bool:
        with self._lock:
            target = next(
                (item for item in self._pending_permissions if item.request_id == request_id),
                None,
            )
        if target is None:
            return False
        target.response = choice
        target.event.set()
        if self._transport_mode in {"subprocess", "websocket", "ssh"}:
            self._send_transport_message(
                {
                    "type": "permission_response",
                    "request_id": request_id,
                    "choice": choice,
                }
            )
        with self._lock:
            self._pending_permissions = [
                item for item in self._pending_permissions if item.request_id != request_id
            ]
        self._append_event(f"permission_resolved request_id={request_id} choice={choice}")
        return True

    def interrupt(self) -> bool:
        with self._lock:
            task = self._active_task
            if task is None or task.status not in {"pending", "running"}:
                return False
            self._cancelled_task_ids.add(task.task_id)
            pending = list(self._pending_permissions)
            self._pending_permissions = []

        for waiter in pending:
            waiter.response = "deny_once"
            waiter.event.set()

        if self._transport_mode in {"subprocess", "websocket", "ssh"}:
            self._send_transport_message(
                {
                    "type": "interrupt",
                    "task_id": task.task_id,
                }
            )

        self._update_task(
            task.task_id,
            status="cancelled",
            error_message="Interrupted by user.",
        )
        self._task_done.set()
        self._append_event(f"interrupt task_id={task.task_id}")
        return True

    def disconnect_transport(self) -> None:
        self.interrupt()
        process = self._process
        websocket = self._websocket

        if process is not None:
            try:
                self._send_transport_message({"type": "shutdown"})
            except Exception:
                pass
            try:
                process.terminate()
            except Exception:
                pass
        if websocket is not None:
            try:
                websocket.close()
            except Exception:
                pass

        self._process = None
        self._process_reader = None
        self._process_stderr_reader = None
        self._websocket = None
        self._websocket_reader = None
        self._transport_mode = "in_process"

    def shutdown(self) -> None:
        self.disconnect_transport()

    def reconnect_transport(self) -> None:
        if self._last_remote_session_id is None or self._last_local_session_id is None:
            return
        self.disconnect_transport()
        self.connect(
            remote_session_id=self._last_remote_session_id,
            local_session_id=self._last_local_session_id,
            transport_mode=self._last_requested_transport,
            session_url=self._last_session_url,
            ssh_host=self._last_ssh_host,
            ssh_remote_cwd=self._last_ssh_remote_cwd,
        )

    def _run_prompt(self, task_id: str, prompt: str) -> None:
        started_at = perf_counter()
        self._update_task(task_id, status="running")
        remote_context = self._clone_context()
        remote_context.metadata["permission_prompt_callback"] = self._request_permission
        remote_context.metadata["current_turn_id"] = None
        history = self.messages()
        query_service = QueryService(
            self._provider,
            tool_service=self._tool_service,
            tool_context=remote_context,
        )
        try:
            result = query_service.submit(
                QueryRequest(
                    prompt=prompt,
                    model=self._model_name,
                    history=history,
                    system_prompt=self._system_prompt,
                    max_tokens=self._default_max_tokens,
                )
            )
        except Exception as exc:
            if task_id in self._cancelled_task_ids:
                self._update_task(task_id, status="cancelled", error_message="Interrupted by user.")
            else:
                self._update_task(task_id, status="failed", error_message=str(exc))
            return

        if task_id in self._cancelled_task_ids:
            self._append_event(f"drop_result task_id={task_id} interrupted=true")
            self._update_task(task_id, status="cancelled", error_message="Interrupted by user.")
            return

        with self._lock:
            assert self._state is not None
            self._state = self._session_service.append_turn(
                self._state,
                result.new_messages,
            )
        self._update_task(
            task_id,
            status="completed",
            result_text=result.text,
            metadata={
                "duration_ms": int((perf_counter() - started_at) * 1000),
                "message_count": len(result.new_messages),
            },
        )

    def _clone_context(self) -> ToolContext:
        metadata = dict(self._tool_context.metadata)
        metadata["conversation_history"] = self.messages()
        metadata["current_model"] = self._model_name
        metadata["system_prompt"] = self._system_prompt
        return ToolContext(
            workspace_root=self._tool_context.workspace_root,
            cwd=self._tool_context.cwd,
            default_model=self._tool_context.default_model,
            llm_provider=self._tool_context.llm_provider,
            shell_provider=self._tool_context.shell_provider,
            metadata=metadata,
        )

    def _request_permission(
        self,
        request: PermissionPromptRequest,
    ) -> PermissionPromptChoice:
        waiter = RemotePermissionRequestState(
            request_id=new_permission_request_id(),
            prompt=request,
        )
        with self._lock:
            self._pending_permissions.append(waiter)
        waiter.event.wait(timeout=300)
        return waiter.response or "deny_once"

    def _spawn_subprocess_worker(
        self,
        *,
        remote_session_id: str,
        local_session_id: str,
    ) -> None:
        env = self._build_worker_env(
            remote_session_id=remote_session_id,
            local_session_id=local_session_id,
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "claude_code_py.providers.remote.worker",
                "--stdio",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=str(self._tool_context.workspace_root),
            env=env,
        )
        self._process = process
        self._process_reader = Thread(target=self._read_process_messages, daemon=True)
        self._process_reader.start()
        if process.stderr is not None:
            self._process_stderr_reader = Thread(
                target=self._read_process_stderr,
                daemon=True,
            )
            self._process_stderr_reader.start()

    def _spawn_ssh_worker(
        self,
        *,
        remote_session_id: str,
        local_session_id: str,
        ssh_host: str,
        ssh_remote_cwd: str | None,
    ) -> None:
        env = self._build_worker_env(
            remote_session_id=remote_session_id,
            local_session_id=local_session_id,
        )
        python_bin = os.environ.get("CLAUDE_CODE_REMOTE_SSH_PYTHON", "python3")
        exports = " ".join(
            f"{key}={shlex.quote(value)}"
            for key, value in env.items()
            if key.startswith("CLAUDE_CODE_REMOTE_WORKER_")
        )
        command_parts = []
        if ssh_remote_cwd:
            command_parts.append(f"cd {shlex.quote(ssh_remote_cwd)}")
        command_parts.append(
            f"env {exports} {shlex.quote(python_bin)} -m "
            "claude_code_py.providers.remote.worker --stdio"
        )
        remote_command = " && ".join(command_parts)
        process = subprocess.Popen(
            ["ssh", ssh_host, remote_command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=str(self._tool_context.workspace_root),
            env=os.environ.copy(),
        )
        self._process = process
        self._process_reader = Thread(target=self._read_process_messages, daemon=True)
        self._process_reader.start()
        if process.stderr is not None:
            self._process_stderr_reader = Thread(
                target=self._read_process_stderr,
                daemon=True,
            )
            self._process_stderr_reader.start()

    def _connect_websocket(self, session_url: str) -> None:
        parsed = urlparse(session_url)
        if parsed.scheme != "ws":
            raise WebSocketTransportError(
                f"Unsupported direct-connect URL '{session_url}'. Expected ws://..."
            )
        self._websocket = connect_websocket(session_url, timeout=0.5)
        self._websocket_reader = Thread(
            target=self._read_websocket_messages,
            daemon=True,
        )
        self._websocket_reader.start()
        self._append_event(f"connected transport=websocket url={session_url}")

    def _build_worker_env(
        self,
        *,
        remote_session_id: str,
        local_session_id: str,
    ) -> dict[str, str]:
        env = os.environ.copy()
        env["CLAUDE_CODE_REMOTE_WORKER_SESSION_ID"] = remote_session_id
        env["CLAUDE_CODE_REMOTE_WORKER_LOCAL_SESSION_ID"] = local_session_id
        env["CLAUDE_CODE_REMOTE_WORKER_MODEL"] = self._model_name
        env["CLAUDE_CODE_REMOTE_WORKER_SYSTEM_PROMPT"] = self._system_prompt or ""
        env["CLAUDE_CODE_REMOTE_WORKER_WORKSPACE_ROOT"] = str(self._tool_context.workspace_root)
        app_container = self._tool_context.metadata.get("app_container")
        if app_container is not None and hasattr(app_container, "paths"):
            env["CLAUDE_CODE_REMOTE_WORKER_PROJECT_ROOT"] = str(app_container.paths.root)
            env["CLAUDE_CODE_REMOTE_WORKER_DATA_DIR"] = str(app_container.paths.data_dir)
            env["CLAUDE_CODE_REMOTE_WORKER_SESSIONS_DIR"] = str(app_container.paths.sessions_dir)
            env["CLAUDE_CODE_REMOTE_WORKER_SESSION_INDEX"] = str(app_container.paths.session_index_path)
            env["CLAUDE_CODE_REMOTE_WORKER_ENV_FILE"] = str(app_container.paths.env_file)
        if self._permission_service is not None:
            rules = self._permission_service.list_rules()
            env["CLAUDE_CODE_REMOTE_WORKER_PERMISSION_MODE"] = self._permission_service.current_mode()
            env["CLAUDE_CODE_REMOTE_WORKER_ALLOW_RULES"] = json.dumps(
                [render_rule(rule) for rule in rules if rule.behavior == "allow"],
                ensure_ascii=False,
            )
            env["CLAUDE_CODE_REMOTE_WORKER_DENY_RULES"] = json.dumps(
                [render_rule(rule) for rule in rules if rule.behavior == "deny"],
                ensure_ascii=False,
            )
            env["CLAUDE_CODE_REMOTE_WORKER_ASK_RULES"] = json.dumps(
                [render_rule(rule) for rule in rules if rule.behavior == "ask"],
                ensure_ascii=False,
            )
        return env

    def _send_transport_message(self, payload: dict[str, object]) -> None:
        with self._transport_lock:
            if self._transport_mode in {"subprocess", "ssh"}:
                process = self._process
                if process is None or process.stdin is None:
                    raise RuntimeError("Remote process transport is not available.")
                process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                process.stdin.flush()
                return
            if self._transport_mode == "websocket":
                websocket = self._websocket
                if websocket is None:
                    raise RuntimeError("Remote WebSocket transport is not available.")
                websocket.send_text(json.dumps(payload, ensure_ascii=False))
                return
            raise RuntimeError("Remote transport is not active.")

    def _read_process_messages(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        while True:
            line = process.stdout.readline()
            if not line:
                return
            self._consume_transport_line(line)

    def _read_process_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        for line in process.stderr:
            text = line.strip()
            if text:
                self._append_event(f"remote_stderr {text}")

    def _read_websocket_messages(self) -> None:
        websocket = self._websocket
        if websocket is None:
            return
        while True:
            try:
                line = websocket.recv_text()
            except Exception as exc:
                self._append_event(f"websocket_disconnected {exc}")
                return
            if line is None:
                self._append_event("websocket_closed")
                return
            self._consume_transport_line(line)

    def _consume_transport_line(self, line: str) -> None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            self._append_event(f"invalid_transport_payload {line[:120]}")
            return
        if isinstance(payload, dict):
            self._handle_transport_message(payload)

    def _handle_transport_message(self, payload: dict[str, object]) -> None:
        message_type = payload.get("type")
        if message_type == "ready":
            self._append_event(
                f"remote_ready session_id={payload.get('session_id') or '(unknown)'}"
            )
            return
        if message_type == "permission_request":
            prompt = payload.get("prompt")
            if not isinstance(prompt, dict):
                return
            waiter = RemotePermissionRequestState(
                request_id=str(payload.get("request_id") or new_permission_request_id()),
                prompt=PermissionPromptRequest.model_validate(prompt),
            )
            with self._lock:
                self._pending_permissions.append(waiter)
            self._append_event(
                f"permission_request request_id={waiter.request_id} tool={waiter.prompt.tool_name}"
            )
            return
        if message_type == "permission_cancel":
            request_id = str(payload.get("request_id") or "")
            if not request_id:
                return
            with self._lock:
                self._pending_permissions = [
                    item for item in self._pending_permissions if item.request_id != request_id
                ]
            self._append_event(f"permission_cancel request_id={request_id}")
            return
        if message_type == "task_status":
            task_id = payload.get("task_id")
            if not isinstance(task_id, str):
                return
            status = str(payload.get("status") or "failed")
            new_messages = payload.get("new_messages")
            if isinstance(new_messages, list):
                parsed_messages = []
                for item in new_messages:
                    if not isinstance(item, dict):
                        continue
                    parsed_messages.append(deserialize_message(item))
                if parsed_messages:
                    with self._lock:
                        if self._state is not None:
                            self._state = self._session_service.append_turn(
                                self._state,
                                parsed_messages,
                            )
            self._update_task(
                task_id,
                status=status,
                result_text=payload.get("result_text") if isinstance(payload.get("result_text"), str) else None,
                error_message=payload.get("error_message") if isinstance(payload.get("error_message"), str) else None,
                metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None,
            )
            self._append_event(f"task_status task_id={task_id} status={status}")
            if status in {"completed", "failed", "cancelled"}:
                self._task_done.set()
            return
        if message_type == "heartbeat":
            self._append_event("heartbeat")
            return
        if message_type == "error":
            self._append_event(f"remote_error {payload.get('message') or '(unknown)'}")

    def _update_task(
        self,
        task_id: str,
        *,
        status: str,
        result_text: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        with self._lock:
            if self._active_task is None or self._active_task.task_id != task_id:
                return
            updated = self._active_task.model_copy(
                update={
                    "status": status,
                    "result_text": result_text if result_text is not None else self._active_task.result_text,
                    "error_message": error_message if error_message is not None else self._active_task.error_message,
                    "metadata": {
                        **self._active_task.metadata,
                        **(metadata or {}),
                    },
                }
            )
            self._active_task = updated

    def _append_event(self, line: str) -> None:
        with self._lock:
            self._event_log.append(line)
            self._event_log = self._event_log[-100:]
