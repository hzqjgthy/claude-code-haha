import json
from pathlib import Path

from claude_code_py.providers.mcp.base import (
    LoadedMcpServerConfig,
    McpConfigDocument,
    McpConfigSource,
)


def load_mcp_server_configs(
    workspace_root: Path,
    *,
    cli_configs: list[str] | None = None,
) -> list[LoadedMcpServerConfig]:
    loaded: dict[str, LoadedMcpServerConfig] = {}

    project_config_path = workspace_root / ".mcp.json"
    if project_config_path.exists():
        document = load_mcp_document(project_config_path)
        for server_name, config in document.mcpServers.items():
            loaded[server_name] = LoadedMcpServerConfig(
                server_name=server_name,
                source="project",
                config=config,
            )

    for raw_config in cli_configs or []:
        document = load_mcp_document(raw_config)
        for server_name, config in document.mcpServers.items():
            loaded[server_name] = LoadedMcpServerConfig(
                server_name=server_name,
                source="cli_arg",
                config=config,
            )

    return list(loaded.values())


def load_mcp_document(value: str | Path) -> McpConfigDocument:
    if isinstance(value, Path):
        raw = value.read_text(encoding="utf-8")
    else:
        candidate = Path(value).expanduser()
        raw = (
            candidate.read_text(encoding="utf-8")
            if candidate.exists()
            else value
        )
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("MCP config must be a JSON object.")
    return McpConfigDocument.model_validate(parsed)
