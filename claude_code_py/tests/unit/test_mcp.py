import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
from pathlib import Path
from threading import Thread

from claude_code_py.application.query_service import QueryRequest, QueryService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.tools import ToolCall
from claude_code_py.providers.llm.base import CompletionRequest, CompletionResponse, LLMProvider
from claude_code_py.providers.mcp import McpConnectionManager, load_mcp_server_configs
from claude_code_py.tools import build_default_tool_registry
from claude_code_py.tools.mcp import McpTool
from tests.helpers import make_tool_context


def fake_mcp_config(script_path: Path) -> str:
    return json.dumps(
        {
            "mcpServers": {
                "demo": {
                    "command": sys.executable,
                    "args": [str(script_path)],
                }
            }
        }
    )


@contextlib.contextmanager
def fake_http_mcp_server():
    class Handler(BaseHTTPRequestHandler):
        session_id = "session-demo"

        def do_POST(self) -> None:  # noqa: N802
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            payload = json.loads(raw.decode("utf-8"))
            method = payload.get("method")
            response: dict[str, object]
            status_code = 200

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "protocolVersion": payload.get("params", {}).get("protocolVersion"),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "fake-http-mcp", "version": "0.1.0"},
                    },
                }
            elif method == "notifications/initialized":
                self.send_response(202)
                self.send_header("Mcp-Session-Id", self.session_id)
                self.end_headers()
                return
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "tools": [
                            {
                                "name": "echo_http",
                                "description": "Echo HTTP MCP input",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"text": {"type": "string"}},
                                    "required": ["text"],
                                },
                            }
                        ]
                    },
                }
            elif method == "tools/call":
                params = payload.get("params", {})
                arguments = params.get("arguments", {}) if isinstance(params, dict) else {}
                text = arguments.get("text", "") if isinstance(arguments, dict) else ""
                response = {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "content": [{"type": "text", "text": f"http-mcp:{text}"}],
                        "isError": False,
                    },
                }
            else:
                status_code = 404
                response = {
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "error": {"message": f"Unknown method: {method}"},
                }

            body = json.dumps(response, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Mcp-Session-Id", self.session_id)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/mcp"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_load_mcp_server_configs_merges_project_and_cli(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "demo": {
                        "command": "python",
                        "args": ["project.py"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    configs = load_mcp_server_configs(
        workspace_root,
        cli_configs=[
            json.dumps(
                {
                    "mcpServers": {
                        "demo": {
                            "command": "python",
                            "args": ["cli.py"],
                        }
                    }
                }
            )
        ],
    )

    assert len(configs) == 1
    assert configs[0].source == "cli_arg"
    assert configs[0].config.args == ["cli.py"]


def test_load_mcp_server_configs_accepts_http_url_without_type(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    configs = load_mcp_server_configs(
        workspace_root,
        cli_configs=[
            json.dumps(
                {
                    "mcpServers": {
                        "xiaohongshu-mcp": {
                            "url": "http://localhost:18060/mcp",
                            "description": "小红书 MCP",
                        }
                    }
                }
            )
        ],
    )

    assert len(configs) == 1
    assert configs[0].server_name == "xiaohongshu-mcp"
    assert configs[0].config.type == "http"
    assert configs[0].config.url == "http://localhost:18060/mcp"


def test_mcp_connection_manager_lists_and_calls_tools(tmp_path) -> None:
    script_path = Path(__file__).resolve().parents[1] / "fixtures" / "fake_mcp_server.py"
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    configs = load_mcp_server_configs(
        workspace_root,
        cli_configs=[fake_mcp_config(script_path)],
    )
    manager = McpConnectionManager.connect_all(configs, workspace_root=workspace_root)

    try:
        tools = manager.list_tool_definitions()
        result = manager.call_tool("demo", "echo_tool", {"text": "hello"})
    finally:
        manager.close()

    assert manager.errors == []
    assert len(tools) == 1
    assert tools[0].qualified_name == "mcp__demo__echo_tool"
    assert result.output == "mcp-echo:hello"
    assert result.is_error is False


def test_http_mcp_connection_manager_lists_and_calls_tools(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    with fake_http_mcp_server() as url:
        configs = load_mcp_server_configs(
            workspace_root,
            cli_configs=[
                json.dumps(
                    {
                        "mcpServers": {
                            "xiaohongshu-mcp": {
                                "url": url,
                                "description": "小红书 MCP",
                            }
                        }
                    }
                )
            ],
        )
        manager = McpConnectionManager.connect_all(
            configs,
            workspace_root=workspace_root,
        )
        try:
            tools = manager.list_tool_definitions()
            result = manager.call_tool(
                "xiaohongshu-mcp",
                "echo_http",
                {"text": "hello"},
            )
        finally:
            manager.close()

    assert manager.errors == []
    assert len(tools) == 1
    assert tools[0].qualified_name == "mcp__xiaohongshu_mcp__echo_http"
    assert result.output == "http-mcp:hello"


def test_http_mcp_connection_manager_records_connection_errors_without_crashing(
    tmp_path,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    configs = load_mcp_server_configs(
        workspace_root,
        cli_configs=[
            json.dumps(
                {
                    "mcpServers": {
                        "xiaohongshu-mcp": {
                            "url": "http://127.0.0.1:1/mcp",
                            "description": "broken http mcp",
                        }
                    }
                }
            )
        ],
    )

    manager = McpConnectionManager.connect_all(
        configs,
        workspace_root=workspace_root,
    )

    try:
        assert manager.server_names() == []
        assert len(manager.errors) == 1
        assert "Failed to initialize HTTP MCP server 'xiaohongshu-mcp'" in manager.errors[0]
    finally:
        manager.close()


def test_mcp_connection_manager_exposes_runtime_states_and_auth_hints(
    tmp_path,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    configs = load_mcp_server_configs(
        workspace_root,
        cli_configs=[
            json.dumps(
                {
                    "mcpServers": {
                        "xiaohongshu-mcp": {
                            "url": "http://127.0.0.1:1/mcp",
                            "description": "broken http mcp",
                        }
                    }
                }
            )
        ],
    )

    manager = McpConnectionManager.connect_all(
        configs,
        workspace_root=workspace_root,
    )

    try:
        states = manager.server_states()
        assert len(states) == 1
        assert states[0].server_name == "xiaohongshu-mcp"
        assert states[0].connected is False
        assert manager.auth_hint("xiaohongshu-mcp")
    finally:
        manager.close()


def test_http_mcp_connection_manager_can_reconnect(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    with fake_http_mcp_server() as url:
        configs = load_mcp_server_configs(
            workspace_root,
            cli_configs=[
                json.dumps(
                    {
                        "mcpServers": {
                            "xiaohongshu-mcp": {
                                "url": url,
                                "description": "小红书 MCP",
                            }
                        }
                    }
                )
            ],
        )
        manager = McpConnectionManager.connect_all(
            configs,
            workspace_root=workspace_root,
        )
        try:
            tools = manager.list_tool_definitions()
            resources = manager.list_resources()
            reconnected = manager.reconnect("xiaohongshu-mcp")
            states = manager.server_states()
        finally:
            manager.close()

    assert len(tools) == 1
    assert isinstance(resources, list)
    assert reconnected == ["xiaohongshu-mcp"]
    assert states[0].connected is True


class McpToolLoopProvider(LLMProvider):
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.calls += 1
        if self.calls == 1:
            assert any(tool.name == "mcp__demo__echo_tool" for tool in request.tools)
            return CompletionResponse(
                model=request.model,
                tool_calls=[
                    ToolCall(
                        tool_use_id="toolu_mcp_1",
                        tool_name="mcp__demo__echo_tool",
                        arguments={"text": "hello"},
                    )
                ],
                raw_response={"phase": 1},
            )
        return CompletionResponse(
            model=request.model,
            text="finished after mcp tool",
            raw_response={"phase": 2},
        )


def test_query_service_executes_mcp_tool_loop(tmp_path) -> None:
    script_path = Path(__file__).resolve().parents[1] / "fixtures" / "fake_mcp_server.py"
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    configs = load_mcp_server_configs(
        workspace_root,
        cli_configs=[fake_mcp_config(script_path)],
    )
    manager = McpConnectionManager.connect_all(configs, workspace_root=workspace_root)
    mcp_tools = [
        McpTool(definition=definition, manager=manager)
        for definition in manager.list_tool_definitions()
    ]
    provider = McpToolLoopProvider()
    context = make_tool_context(tmp_path)

    try:
        service = QueryService(
            provider,
            tool_service=ToolService(
                build_default_tool_registry(extra_tools=mcp_tools),
            ),
            tool_context=context,
        )
        result = service.submit(
            QueryRequest(
                prompt="use mcp",
                model="test-model",
            ),
        )
    finally:
        manager.close()

    assert provider.calls == 2
    assert result.text == "finished after mcp tool"
    assert [message.kind for message in result.new_messages] == [
        "user",
        "tool_use",
        "tool_result",
        "assistant",
    ]
