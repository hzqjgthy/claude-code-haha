import json
import os
from abc import ABC, abstractmethod
from collections import deque
from itertools import count
from pathlib import Path
from queue import Empty, Queue
import subprocess
from threading import Lock, Thread
from typing import Any

import httpx

from claude_code_py.providers.mcp.base import (
    MCP_PROTOCOL_VERSION,
    LoadedMcpServerConfig,
    McpHttpServerConfig,
    McpResourceDefinition,
    McpServerRuntimeState,
    McpStdioServerConfig,
    McpToolCallResult,
    McpToolDefinition,
)

MCP_STREAMABLE_HTTP_ACCEPT = "application/json, text/event-stream"
MCP_SESSION_HEADER = "mcp-session-id"


class McpError(RuntimeError):
    """Raised when an MCP server cannot be loaded or called."""


class BaseMcpClient(ABC):
    def __init__(self, server: LoadedMcpServerConfig) -> None:
        self._server = server

    @property
    def server_name(self) -> str:
        return self._server.server_name

    def list_tools(self) -> list[McpToolDefinition]:
        response = self.request("tools/list", {})
        result = response.get("result")
        if not isinstance(result, dict):
            raise McpError(
                f"MCP server '{self.server_name}' returned an invalid tools/list payload.",
            )
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise McpError(
                f"MCP server '{self.server_name}' returned invalid tools.",
            )
        parsed: list[McpToolDefinition] = []
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            name = tool.get("name")
            if not isinstance(name, str) or not name:
                continue
            description = tool.get("description")
            input_schema = tool.get("inputSchema") or tool.get("input_schema") or {}
            if not isinstance(input_schema, dict):
                input_schema = {}
            parsed.append(
                McpToolDefinition(
                    server_name=self.server_name,
                    tool_name=name,
                    description=description if isinstance(description, str) else "",
                    input_schema=input_schema,
                ),
            )
        return parsed

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpToolCallResult:
        response = self.request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )
        result = response.get("result")
        if not isinstance(result, dict):
            raise McpError(
                f"MCP tool '{tool_name}' returned an invalid payload.",
            )
        return McpToolCallResult(
            tool_name=tool_name,
            output=render_mcp_content(result.get("content")),
            is_error=bool(result.get("isError", False)),
            raw_result=result,
        )

    def list_resources(self) -> list[McpResourceDefinition]:
        response = self.request("resources/list", {})
        result = response.get("result")
        if not isinstance(result, dict):
            raise McpError(
                f"MCP server '{self.server_name}' returned an invalid resources/list payload.",
            )
        resources = result.get("resources", [])
        if not isinstance(resources, list):
            raise McpError(
                f"MCP server '{self.server_name}' returned invalid resources.",
            )
        parsed: list[McpResourceDefinition] = []
        for resource in resources:
            if not isinstance(resource, dict):
                continue
            uri = resource.get("uri")
            if not isinstance(uri, str) or not uri:
                continue
            parsed.append(
                McpResourceDefinition(
                    server_name=self.server_name,
                    uri=uri,
                    name=resource.get("name")
                    if isinstance(resource.get("name"), str)
                    else None,
                    description=resource.get("description")
                    if isinstance(resource.get("description"), str)
                    else None,
                    mime_type=resource.get("mimeType")
                    if isinstance(resource.get("mimeType"), str)
                    else None,
                )
            )
        return parsed

    def read_resource(
        self,
        uri: str,
    ) -> dict[str, Any]:
        response = self.request(
            "resources/read",
            {
                "uri": uri,
            },
        )
        result = response.get("result")
        if not isinstance(result, dict):
            raise McpError(
                f"MCP resource '{uri}' returned an invalid payload.",
            )
        return result

    @abstractmethod
    def request(
        self,
        method: str,
        params: dict[str, object] | None = None,
        *,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class McpStdioClient(BaseMcpClient):
    def __init__(self, server: LoadedMcpServerConfig, *, workspace_root: Path) -> None:
        super().__init__(server)
        assert isinstance(server.config, McpStdioServerConfig)
        self._workspace_root = workspace_root
        self._request_ids = count(1)
        self._pending: dict[int, Queue[dict[str, Any]]] = {}
        self._write_lock = Lock()
        self._stderr_tail: deque[str] = deque(maxlen=50)
        self._closed = False

        env = os.environ.copy()
        env.update(server.config.env)
        command = [server.config.command, *server.config.args]
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=server.resolve_cwd(workspace_root),
                env=env,
            )
        except OSError as exc:
            raise McpError(
                f"Failed to start MCP server '{server.server_name}': {exc}",
            ) from exc

        if (
            self._process.stdin is None
            or self._process.stdout is None
            or self._process.stderr is None
        ):
            self.close()
            raise McpError(
                f"MCP server '{server.server_name}' did not expose stdio pipes.",
            )

        self._reader = Thread(target=self._reader_loop, daemon=True)
        self._stderr_reader = Thread(target=self._stderr_loop, daemon=True)
        self._reader.start()
        self._stderr_reader.start()
        self._initialize()

    def request(
        self,
        method: str,
        params: dict[str, object] | None = None,
        *,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        request_id = next(self._request_ids)
        response_queue: Queue[dict[str, Any]] = Queue(maxsize=1)
        self._pending[request_id] = response_queue
        self._write_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            },
        )
        try:
            response = response_queue.get(timeout=timeout)
        except Empty as exc:
            self._pending.pop(request_id, None)
            raise McpError(self._timeout_error(method)) from exc
        if "error" in response:
            raise McpError(
                f"MCP server '{self.server_name}' error for {method}: "
                f"{render_error_payload(response['error'])}",
            )
        return response

    def notify(self, method: str, params: dict[str, object] | None = None) -> None:
        self._write_message(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
            },
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)

    def _initialize(self) -> None:
        self.request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "claude-code-py",
                    "version": "0.1.0",
                },
            },
        )
        self.notify("notifications/initialized", {})

    def _write_message(self, payload: dict[str, object]) -> None:
        if self._process.stdin is None:
            raise McpError(f"MCP server '{self.server_name}' stdin is unavailable.")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        message = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8") + body
        with self._write_lock:
            try:
                self._process.stdin.write(message)
                self._process.stdin.flush()
            except OSError as exc:
                raise McpError(
                    f"Failed to write to MCP server '{self.server_name}': {exc}",
                ) from exc

    def _reader_loop(self) -> None:
        assert self._process.stdout is not None
        try:
            while True:
                message = read_mcp_message(self._process.stdout)
                if message is None:
                    return
                raw_id = message.get("id")
                if not isinstance(raw_id, int):
                    continue
                queue = self._pending.pop(raw_id, None)
                if queue is None:
                    continue
                queue.put(message)
        finally:
            for request_id, queue in list(self._pending.items()):
                self._pending.pop(request_id, None)
                queue.put(
                    {
                        "error": {
                            "message": self._process_error_message(),
                        }
                    },
                )

    def _stderr_loop(self) -> None:
        assert self._process.stderr is not None
        while True:
            line = self._process.stderr.readline()
            if not line:
                return
            decoded = line.decode("utf-8", errors="replace").rstrip()
            if decoded:
                self._stderr_tail.append(decoded)

    def _timeout_error(self, method: str) -> str:
        return (
            f"MCP server '{self.server_name}' timed out while waiting for {method}. "
            f"{self._process_error_message()}"
        )

    def _process_error_message(self) -> str:
        returncode = self._process.poll()
        stderr = "\n".join(self._stderr_tail).strip()
        parts = []
        if returncode is not None:
            parts.append(f"process exited with code {returncode}")
        if stderr:
            parts.append(f"stderr: {stderr}")
        return " ".join(parts) or "No additional server diagnostics available."


class McpHttpClient(BaseMcpClient):
    def __init__(self, server: LoadedMcpServerConfig) -> None:
        super().__init__(server)
        assert isinstance(server.config, McpHttpServerConfig)
        self._config = server.config
        self._request_ids = count(1)
        self._session_id: str | None = None
        self._http_client = httpx.Client(
            timeout=self._config.timeout_ms / 1000,
            trust_env=False,
        )
        try:
            self._initialize()
        except httpx.HTTPError as exc:
            self._http_client.close()
            raise McpError(
                f"Failed to initialize HTTP MCP server '{self.server_name}': {exc}",
            ) from exc

    def request(
        self,
        method: str,
        params: dict[str, object] | None = None,
        *,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        request_id = next(self._request_ids)
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        try:
            response = self._post(payload, timeout=timeout)
        except httpx.HTTPError as exc:
            raise McpError(
                f"HTTP MCP server '{self.server_name}' request failed: {exc}",
            ) from exc

        if response.status_code == 404 and self._session_id is not None:
            self._session_id = None
            self._initialize()
            response = self._post(payload, timeout=timeout)

        if response.status_code >= 400:
            raise McpError(
                f"HTTP MCP server '{self.server_name}' returned HTTP {response.status_code}: "
                f"{response.text.strip()}",
            )
        self._update_session_id(response)
        parsed = parse_http_mcp_response(response, expected_id=request_id)
        if "error" in parsed:
            raise McpError(
                f"HTTP MCP server '{self.server_name}' error for {method}: "
                f"{render_error_payload(parsed['error'])}",
            )
        return parsed

    def close(self) -> None:
        try:
            if self._session_id is not None:
                self._http_client.request(
                    "DELETE",
                    self._config.url,
                    headers={
                        MCP_SESSION_HEADER: self._session_id,
                    },
                )
        except httpx.HTTPError:
            pass
        finally:
            self._http_client.close()

    def _initialize(self) -> None:
        payload = {
            "jsonrpc": "2.0",
            "id": next(self._request_ids),
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "claude-code-py",
                    "version": "0.1.0",
                },
            },
        }
        try:
            response = self._post(payload, timeout=self._config.timeout_ms / 1000)
        except httpx.HTTPError as exc:
            raise McpError(
                f"Failed to initialize HTTP MCP server '{self.server_name}': {exc}",
            ) from exc
        if response.status_code >= 400:
            raise McpError(
                f"Failed to initialize HTTP MCP server '{self.server_name}': "
                f"HTTP {response.status_code} {response.text.strip()}",
            )
        self._update_session_id(response)
        parse_http_mcp_response(response, expected_id=payload["id"])
        self._notify_initialized()

    def _post(self, payload: dict[str, object], *, timeout: float) -> httpx.Response:
        headers = {
            "accept": MCP_STREAMABLE_HTTP_ACCEPT,
            "content-type": "application/json",
            **self._config.headers,
        }
        if self._session_id is not None:
            headers[MCP_SESSION_HEADER] = self._session_id
        return self._http_client.post(
            self._config.url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )

    def _update_session_id(self, response: httpx.Response) -> None:
        session_id = response.headers.get(MCP_SESSION_HEADER)
        if session_id:
            self._session_id = session_id

    def _notify_initialized(self) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        try:
            response = self._post(
                payload,
                timeout=self._config.timeout_ms / 1000,
            )
            self._update_session_id(response)
        except httpx.HTTPError:
            return


class McpConnectionManager:
    def __init__(self) -> None:
        self._servers: dict[str, LoadedMcpServerConfig] = {}
        self._clients: dict[str, BaseMcpClient] = {}
        self._states: dict[str, McpServerRuntimeState] = {}
        self._workspace_root: Path | None = None
        self.errors: list[str] = []

    @classmethod
    def connect_all(
        cls,
        servers: list[LoadedMcpServerConfig],
        *,
        workspace_root: Path,
    ) -> "McpConnectionManager":
        manager = cls()
        manager._workspace_root = workspace_root
        for server in servers:
            manager._servers[server.server_name] = server
            manager._states[server.server_name] = McpServerRuntimeState(
                server_name=server.server_name,
                source=server.source,
                transport="http" if isinstance(server.config, McpHttpServerConfig) else "stdio",
                connected=False,
            )
            try:
                manager._clients[server.server_name] = build_mcp_client(
                    server,
                    workspace_root=workspace_root,
                )
                manager._states[server.server_name].connected = True
            except McpError as exc:
                manager.errors.append(str(exc))
                manager._record_error(server.server_name, str(exc))
            except Exception as exc:
                manager.errors.append(str(exc))
                manager._record_error(server.server_name, str(exc))
        return manager

    def list_tool_definitions(self) -> list[McpToolDefinition]:
        tools: list[McpToolDefinition] = []
        counts: dict[str, int] = {}
        for client in self._clients.values():
            try:
                current = client.list_tools()
                tools.extend(current)
                counts[client.server_name] = len(current)
                self._mark_connected(client.server_name)
            except McpError as exc:
                self.errors.append(str(exc))
                self._record_error(client.server_name, str(exc))
        for server_name, state in self._states.items():
            state.tool_count = counts.get(server_name, state.tool_count)
        return tools

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpToolCallResult:
        try:
            client = self._clients[server_name]
        except KeyError as exc:
            raise McpError(f"Unknown MCP server '{server_name}'.") from exc
        try:
            result = client.call_tool(tool_name, arguments)
            self._mark_connected(server_name)
            return result
        except McpError as exc:
            self._record_error(server_name, str(exc))
            raise

    def list_resources(
        self,
        server_name: str | None = None,
    ) -> list[McpResourceDefinition]:
        if server_name is not None:
            try:
                clients = [self._clients[server_name]]
            except KeyError as exc:
                raise McpError(f"Unknown MCP server '{server_name}'.") from exc
        else:
            clients = list(self._clients.values())
        resources: list[McpResourceDefinition] = []
        counts: dict[str, int] = {}
        for client in clients:
            try:
                current = client.list_resources()
                resources.extend(current)
                counts[client.server_name] = len(current)
                self._mark_connected(client.server_name)
            except McpError as exc:
                self.errors.append(str(exc))
                self._record_error(client.server_name, str(exc))
        for name, state in self._states.items():
            if server_name is None or name == server_name:
                state.resource_count = counts.get(name, state.resource_count)
        return resources

    def read_resource(
        self,
        server_name: str,
        uri: str,
    ) -> dict[str, Any]:
        try:
            client = self._clients[server_name]
        except KeyError as exc:
            raise McpError(f"Unknown MCP server '{server_name}'.") from exc
        try:
            result = client.read_resource(uri)
            self._mark_connected(server_name)
            return result
        except McpError as exc:
            self._record_error(server_name, str(exc))
            raise

    def server_names(self) -> list[str]:
        return sorted(self._clients)

    def server_states(self) -> list[McpServerRuntimeState]:
        return [
            state.model_copy(deep=True)
            for _, state in sorted(self._states.items(), key=lambda item: item[0])
        ]

    def reconnect(self, server_name: str | None = None) -> list[str]:
        if self._workspace_root is None:
            raise McpError("MCP workspace root is unavailable for reconnect.")
        target_names = [server_name] if server_name is not None else sorted(self._servers)
        reconnected: list[str] = []
        for name in target_names:
            server = self._servers.get(name)
            if server is None:
                raise McpError(f"Unknown MCP server '{name}'.")
            existing = self._clients.pop(name, None)
            if existing is not None:
                existing.close()
            try:
                self._clients[name] = build_mcp_client(
                    server,
                    workspace_root=self._workspace_root,
                )
                self._states[name].connected = True
                self._states[name].last_error = None
                self._states[name].auth_required = False
                reconnected.append(name)
            except Exception as exc:
                self._record_error(name, str(exc))
                self.errors.append(str(exc))
        return reconnected

    def auth_hint(self, server_name: str) -> str:
        server = self._servers.get(server_name)
        state = self._states.get(server_name)
        if server is None or state is None:
            raise McpError(f"Unknown MCP server '{server_name}'.")
        if isinstance(server.config, McpHttpServerConfig):
            if state.auth_required:
                return (
                    f"Server '{server_name}' appears to require HTTP auth. "
                    f"Check headers or tokens for {server.config.url} and reconnect."
                )
            return (
                f"HTTP MCP server '{server_name}' is configured at {server.config.url}. "
                "If it requires auth, update headers in .mcp.json or the CLI config."
            )
        return (
            f"stdio MCP server '{server_name}' uses command '{server.config.command}'. "
            "Complete any login flow required by that command, then run /mcp reconnect."
        )

    def close(self) -> None:
        for client in self._clients.values():
            client.close()

    def _mark_connected(self, server_name: str) -> None:
        state = self._states.get(server_name)
        if state is None:
            return
        state.connected = True
        state.last_error = None
        state.auth_required = False

    def _record_error(self, server_name: str, message: str) -> None:
        state = self._states.get(server_name)
        if state is None:
            return
        state.connected = False
        state.last_error = message
        state.auth_required = _looks_like_auth_error(message)


def build_mcp_client(
    server: LoadedMcpServerConfig,
    *,
    workspace_root: Path,
) -> BaseMcpClient:
    if isinstance(server.config, McpStdioServerConfig):
        return McpStdioClient(server, workspace_root=workspace_root)
    if isinstance(server.config, McpHttpServerConfig):
        return McpHttpClient(server)
    raise McpError(
        f"Unsupported MCP transport for server '{server.server_name}': {server.config}",
    )


def _looks_like_auth_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in ["401", "403", "unauthorized", "forbidden", "needs auth", "authentication"]
    )


def read_mcp_message(stream) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        decoded = line.decode("utf-8", errors="replace").strip()
        if not decoded:
            continue
        key, _, value = decoded.partition(":")
        headers[key.lower()] = value.strip()
    content_length = int(headers.get("content-length", "0"))
    if content_length <= 0:
        return None
    body = stream.read(content_length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def parse_http_mcp_response(
    response: httpx.Response,
    *,
    expected_id: int,
) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "").lower()
    if "text/event-stream" in content_type:
        parsed = parse_sse_mcp_response(response.text, expected_id=expected_id)
        if parsed is None:
            raise McpError("HTTP MCP server returned SSE without a matching JSON-RPC response.")
        return parsed
    if not response.text.strip():
        raise McpError("HTTP MCP server returned an empty response body.")
    payload = response.json()
    if not isinstance(payload, dict):
        raise McpError("HTTP MCP server returned a non-object JSON payload.")
    return payload


def parse_sse_mcp_response(
    raw_text: str,
    *,
    expected_id: int,
) -> dict[str, Any] | None:
    events = raw_text.replace("\r\n", "\n").split("\n\n")
    for event in events:
        data_lines = []
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            data_lines.append(line[5:].lstrip())
        if not data_lines:
            continue
        try:
            payload = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("id") == expected_id:
            return payload
    return None


def render_mcp_content(content: object) -> str:
    if not isinstance(content, list):
        return json.dumps(content, ensure_ascii=False)
    rendered: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            rendered.append(json.dumps(block, ensure_ascii=False))
            continue
        block_type = block.get("type")
        if block_type == "text" and isinstance(block.get("text"), str):
            rendered.append(block["text"])
            continue
        rendered.append(json.dumps(block, ensure_ascii=False))
    return "\n".join(part for part in rendered if part).strip()


def render_error_payload(payload: object) -> str:
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str):
            return message
    return json.dumps(payload, ensure_ascii=False)
