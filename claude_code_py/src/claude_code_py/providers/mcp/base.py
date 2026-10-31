from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

McpTransport = Literal["stdio", "http"]
McpConfigSource = Literal["project", "cli_arg"]

MCP_PROTOCOL_VERSION = "2025-03-26"


class McpStdioServerConfig(BaseModel):
    type: Literal["stdio"] = "stdio"
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None


class McpHttpServerConfig(BaseModel):
    type: Literal["http"] = "http"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_ms: int = 30_000


McpServerConfig = McpStdioServerConfig | McpHttpServerConfig


class McpConfigDocument(BaseModel):
    mcpServers: dict[str, McpServerConfig] = Field(default_factory=dict)


class LoadedMcpServerConfig(BaseModel):
    server_name: str
    source: McpConfigSource
    config: McpServerConfig

    def resolve_cwd(self, workspace_root: Path) -> Path:
        if not isinstance(self.config, McpStdioServerConfig):
            return workspace_root
        if self.config.cwd is None:
            return workspace_root
        candidate = Path(self.config.cwd).expanduser()
        if not candidate.is_absolute():
            candidate = workspace_root / candidate
        return candidate.resolve()


class McpToolDefinition(BaseModel):
    server_name: str
    tool_name: str
    description: str = ""
    input_schema: dict[str, object] = Field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        return build_mcp_tool_name(self.server_name, self.tool_name)


class McpToolCallResult(BaseModel):
    tool_name: str
    output: str
    is_error: bool = False
    raw_result: dict[str, object] = Field(default_factory=dict)


class McpResourceDefinition(BaseModel):
    server_name: str
    uri: str
    name: str | None = None
    description: str | None = None
    mime_type: str | None = None


class McpServerRuntimeState(BaseModel):
    server_name: str
    source: McpConfigSource
    transport: McpTransport
    connected: bool = False
    auth_required: bool = False
    tool_count: int = 0
    resource_count: int = 0
    last_error: str | None = None


def normalize_mcp_name(value: str) -> str:
    normalized = []
    for char in value.strip().lower():
        if char.isalnum():
            normalized.append(char)
        else:
            normalized.append("_")
    slug = "".join(normalized).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "tool"


def build_mcp_tool_name(server_name: str, tool_name: str) -> str:
    return f"mcp__{normalize_mcp_name(server_name)}__{normalize_mcp_name(tool_name)}"
