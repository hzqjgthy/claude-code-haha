from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import socket
import sys
from threading import Event, Lock, Thread
from time import sleep

from claude_code_py.app.container import AppContainer
from claude_code_py.app.settings import AppSettings
from claude_code_py.application.permission_service import PermissionService
from claude_code_py.application.query_service import QueryRequest, QueryService
from claude_code_py.application.session_service import SessionService
from claude_code_py.application.task_service import TaskService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.cli.print_mode import build_llm_provider
from claude_code_py.common.logging import configure_logging, get_logger
from claude_code_py.common.paths import ProjectPaths, build_project_paths
from claude_code_py.domain.messages import serialize_message
from claude_code_py.domain.permissions import PermissionPromptChoice, PermissionPromptRequest
from claude_code_py.domain.tools import ToolCall
from claude_code_py.providers.llm.base import CompletionRequest, CompletionResponse, LLMProvider
from claude_code_py.providers.mcp import McpConnectionManager, load_mcp_server_configs
from claude_code_py.providers.remote.websocket_transport import (
    WebSocketTextStream,
    accept_websocket_connection,
)
from claude_code_py.providers.shell import SubprocessShellProvider
from claude_code_py.providers.storage.session_index import SqliteSessionIndex
from claude_code_py.providers.storage.transcript_store import JsonlTranscriptStore
from claude_code_py.tools import build_default_tool_registry
from claude_code_py.tools.base import ToolContext
from claude_code_py.tools.mcp import McpTool


@dataclass(slots=True)
class _PendingPermission:
    request_id: str
    prompt: PermissionPromptRequest
    event: Event = field(default_factory=Event)
    response: PermissionPromptChoice | None = None


class _EchoRemoteProvider(LLMProvider):
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        last_message = request.messages[-1]
        if last_message.kind == "tool_result":
            return CompletionResponse(
                model=request.model,
                text="remote-finished",
                raw_response={"phase": "assistant"},
            )
        prompt = last_message.content  # type: ignore[union-attr]
        if "remote write" in prompt:
            return CompletionResponse(
                model=request.model,
                stop_reason="tool_use",
                tool_calls=[
                    ToolCall(
                        tool_use_id="toolu_remote_1",
                        tool_name="Write",
                        arguments={
                            "file_path": "remote.txt",
                            "content": "hello remote",
                        },
                    )
                ],
                raw_response={"phase": "tool"},
            )
        return CompletionResponse(
            model=request.model,
            text=f"remote:{prompt}",
            raw_response={"phase": "assistant"},
        )


class RemoteWorker:
    def __init__(self) -> None:
        workspace_root = Path(
            os.environ["CLAUDE_CODE_REMOTE_WORKER_WORKSPACE_ROOT"]
        ).resolve()
        os.chdir(workspace_root)
        self._container = _create_worker_container()
        self._model_name = os.environ["CLAUDE_CODE_REMOTE_WORKER_MODEL"]
        self._system_prompt = os.environ.get("CLAUDE_CODE_REMOTE_WORKER_SYSTEM_PROMPT") or None
        self._session_id = os.environ["CLAUDE_CODE_REMOTE_WORKER_SESSION_ID"]
        self._provider = (
            _EchoRemoteProvider()
            if os.environ.get("CLAUDE_CODE_REMOTE_WORKER_TEST_MODE") == "echo"
            else build_llm_provider(self._container)
        )
        self._session_service = SessionService(
            JsonlTranscriptStore(self._container.paths),
            SqliteSessionIndex(self._container.paths.session_index_path),
        )
        self._state = self._session_service.load_or_create(self._session_id)
        self._tool_context = ToolContext(
            workspace_root=workspace_root,
            cwd=workspace_root,
            default_model=self._model_name,
            llm_provider=self._provider,
            shell_provider=SubprocessShellProvider(),
            metadata={},
        )
        mcp_configs = load_mcp_server_configs(workspace_root, cli_configs=[])
        self._mcp_manager = McpConnectionManager.connect_all(
            mcp_configs,
            workspace_root=workspace_root,
        )
        mcp_tools = [
            McpTool(definition=definition, manager=self._mcp_manager)
            for definition in self._mcp_manager.list_tool_definitions()
        ]
        self._permission_service = PermissionService.from_sources(
            container=self._container,
            workspace_root=workspace_root,
            mode=os.environ.get("CLAUDE_CODE_REMOTE_WORKER_PERMISSION_MODE", "default"),
            ask_mode_enabled=True,
            allow_rules=_load_json_list("CLAUDE_CODE_REMOTE_WORKER_ALLOW_RULES"),
            deny_rules=_load_json_list("CLAUDE_CODE_REMOTE_WORKER_DENY_RULES"),
            ask_rules=_load_json_list("CLAUDE_CODE_REMOTE_WORKER_ASK_RULES"),
        )
        self._tool_service = ToolService(
            build_default_tool_registry(extra_tools=[*mcp_tools]),
            permission_service=self._permission_service,
        )
        self._task_service = TaskService(allow_background=False)
        self._task_service.configure(
            provider=self._provider,
            tool_service=self._tool_service,
            tool_context=self._tool_context,
            default_max_tokens=self._container.settings.default_max_tokens,
        )
        self._tool_context.metadata["task_service"] = self._task_service
        self._tool_context.metadata["session_id"] = self._session_id
        self._tool_context.metadata["runtime_state_store"] = None
        self._tool_context.metadata["app_container"] = self._container
        self._tool_context.metadata["mcp_manager"] = self._mcp_manager
        self._tool_context.metadata["tool_registry"] = self._tool_service.registry
        self._tool_context.metadata["permission_prompt_callback"] = self._request_permission
        self._query_service = QueryService(
            self._provider,
            tool_service=self._tool_service,
            tool_context=self._tool_context,
        )
        self._lock = Lock()
        self._write_lock = Lock()
        self._pending_permissions: dict[str, _PendingPermission] = {}
        self._send_callback = self._send_stdout
        self._current_task_id: str | None = None
        self._cancel_event = Event()
        self._cancel_notified_task_id: str | None = None

    def run_stdio(self) -> int:
        self._send({"type": "ready", "session_id": self._session_id})
        return self._run_message_loop(_iter_stdin())

    def run_websocket_server(self, host: str, port: int) -> int:
        server = socket.create_server((host, port), backlog=5)
        actual_host, actual_port = server.getsockname()[:2]
        self._send_stdout(
            {
                "type": "listening",
                "transport": "websocket",
                "host": actual_host,
                "port": actual_port,
                "session_id": self._session_id,
            }
        )
        while True:
            conn, _ = server.accept()
            try:
                websocket = accept_websocket_connection(conn)
            except Exception:
                conn.close()
                continue
            try:
                self._serve_websocket_session(websocket)
            finally:
                websocket.close()

    def _serve_websocket_session(self, websocket: WebSocketTextStream) -> None:
        with self._lock:
            self._send_callback = lambda payload: websocket.send_text(
                json.dumps(payload, ensure_ascii=False)
            )
        self._send({"type": "ready", "session_id": self._session_id})
        while True:
            try:
                raw = websocket.recv_text()
            except Exception:
                break
            if raw is None:
                break
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            should_stop = self._handle_payload(payload)
            if should_stop:
                break
        with self._lock:
            self._send_callback = self._send_stdout

    def _run_message_loop(self, payloads) -> int:
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            should_stop = self._handle_payload(payload)
            if should_stop:
                return 0
        return 0

    def _handle_payload(self, payload: dict[str, object]) -> bool:
        message_type = payload.get("type")
        if message_type == "shutdown":
            self._interrupt_current_task()
            return True
        if message_type == "submit_prompt":
            task_id = str(payload.get("task_id"))
            prompt = str(payload.get("prompt") or "")
            worker = Thread(
                target=self._run_prompt,
                args=(task_id, prompt),
                daemon=True,
            )
            worker.start()
            return False
        if message_type == "permission_response":
            request_id = str(payload.get("request_id"))
            waiter = self._pending_permissions.get(request_id)
            if waiter is None:
                return False
            waiter.response = str(payload.get("choice") or "deny_once")  # type: ignore[assignment]
            waiter.event.set()
            return False
        if message_type == "interrupt":
            self._interrupt_current_task()
            return False
        return False

    def _run_prompt(self, task_id: str, prompt: str) -> None:
        with self._lock:
            self._current_task_id = task_id
            self._cancel_event.clear()
            self._cancel_notified_task_id = None
        self._send({"type": "task_status", "task_id": task_id, "status": "running"})

        if (
            os.environ.get("CLAUDE_CODE_REMOTE_WORKER_TEST_MODE") == "echo"
            and "remote slow" in prompt
        ):
            for _ in range(20):
                if self._cancel_event.is_set():
                    self._notify_cancelled(task_id)
                    return
                sleep(0.05)

        try:
            result = self._query_service.submit(
                QueryRequest(
                    prompt=prompt,
                    model=self._model_name,
                    history=list(self._state.messages),
                    system_prompt=self._system_prompt,
                    max_tokens=self._container.settings.default_max_tokens,
                )
            )
        except Exception as exc:
            if self._cancel_event.is_set():
                self._notify_cancelled(task_id)
            else:
                self._send(
                    {
                        "type": "task_status",
                        "task_id": task_id,
                        "status": "failed",
                        "error_message": str(exc),
                    }
                )
            self._clear_current_task(task_id)
            return

        if self._cancel_event.is_set():
            self._notify_cancelled(task_id)
            self._clear_current_task(task_id)
            return

        self._state = self._session_service.append_turn(
            self._state,
            result.new_messages,
        )
        self._send(
            {
                "type": "task_status",
                "task_id": task_id,
                "status": "completed",
                "result_text": result.text,
                "new_messages": [
                    serialize_message(message)
                    for message in result.new_messages
                ],
            }
        )
        self._clear_current_task(task_id)

    def _request_permission(self, request: PermissionPromptRequest) -> PermissionPromptChoice:
        waiter = _PendingPermission(
            request_id=(
                request.metadata.get("remote_request_id")
                if isinstance(request.metadata, dict)
                and isinstance(request.metadata.get("remote_request_id"), str)
                else os.urandom(8).hex()
            ),
            prompt=request,
        )
        with self._lock:
            self._pending_permissions[waiter.request_id] = waiter
        self._send(
            {
                "type": "permission_request",
                "request_id": waiter.request_id,
                "prompt": request.model_dump(mode="json"),
            }
        )
        waiter.event.wait(timeout=300)
        with self._lock:
            self._pending_permissions.pop(waiter.request_id, None)
        return waiter.response or "deny_once"

    def _interrupt_current_task(self) -> None:
        with self._lock:
            self._cancel_event.set()
            current_task_id = self._current_task_id
            pending = list(self._pending_permissions.values())
            self._pending_permissions = {}

        for waiter in pending:
            waiter.response = "deny_once"
            waiter.event.set()
            self._send(
                {
                    "type": "permission_cancel",
                    "request_id": waiter.request_id,
                }
            )

        if current_task_id is not None:
            self._notify_cancelled(current_task_id)

    def _notify_cancelled(self, task_id: str) -> None:
        with self._lock:
            if self._cancel_notified_task_id == task_id:
                return
            self._cancel_notified_task_id = task_id
        self._send(
            {
                "type": "task_status",
                "task_id": task_id,
                "status": "cancelled",
                "error_message": "Interrupted by user.",
            }
        )

    def _clear_current_task(self, task_id: str) -> None:
        with self._lock:
            if self._current_task_id == task_id:
                self._current_task_id = None
                self._cancel_event.clear()
                self._cancel_notified_task_id = None

    def _send(self, payload: dict[str, object]) -> None:
        with self._write_lock:
            self._send_callback(payload)

    @staticmethod
    def _send_stdout(payload: dict[str, object]) -> None:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def _iter_stdin():
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        yield payload


def _load_json_list(env_name: str) -> list[str]:
    raw = os.environ.get(env_name)
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="claude_code_py.providers.remote.worker")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run the worker over stdio JSON lines.",
    )
    parser.add_argument(
        "--websocket-server",
        nargs=2,
        metavar=("HOST", "PORT"),
        help="Run the worker as a WebSocket server on HOST PORT.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    worker = RemoteWorker()
    if args.websocket_server:
        host, raw_port = args.websocket_server
        return worker.run_websocket_server(host, int(raw_port))
    return worker.run_stdio()


def _create_worker_container() -> AppContainer:
    settings = AppSettings()
    paths = _build_worker_paths()
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.sessions_dir.mkdir(parents=True, exist_ok=True)
    paths.session_index_path.parent.mkdir(parents=True, exist_ok=True)
    configure_logging(settings.log_level)
    logger = get_logger("claude_code_py.remote_worker")
    return AppContainer(settings=settings, paths=paths, logger=logger)


def _build_worker_paths() -> ProjectPaths:
    root = os.environ.get("CLAUDE_CODE_REMOTE_WORKER_PROJECT_ROOT")
    data_dir = os.environ.get("CLAUDE_CODE_REMOTE_WORKER_DATA_DIR")
    sessions_dir = os.environ.get("CLAUDE_CODE_REMOTE_WORKER_SESSIONS_DIR")
    session_index = os.environ.get("CLAUDE_CODE_REMOTE_WORKER_SESSION_INDEX")
    env_file = os.environ.get("CLAUDE_CODE_REMOTE_WORKER_ENV_FILE")
    if not all([root, data_dir, sessions_dir, session_index, env_file]):
        return build_project_paths()
    root_path = Path(root).resolve()
    return ProjectPaths(
        root=root_path,
        src_root=root_path / "src",
        package_root=root_path / "src" / "claude_code_py",
        docs_dir=root_path / "docs",
        tests_dir=root_path / "tests",
        scripts_dir=root_path / "scripts",
        data_dir=Path(data_dir).resolve(),
        sessions_dir=Path(sessions_dir).resolve(),
        session_index_path=Path(session_index).resolve(),
        env_file=Path(env_file).resolve(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
