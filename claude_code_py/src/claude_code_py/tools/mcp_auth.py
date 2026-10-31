from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.providers.mcp import McpConnectionManager
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.domain.tools import ToolExecutionResult


class McpAuthToolInput(BaseModel):
    server: str


class McpAuthTool(BaseTool[McpAuthToolInput]):
    name = "McpAuth"
    description = "Start MCP authentication or explain the auth path."
    input_model = McpAuthToolInput
    read_only = False
    destructive = False

    def summarize(self, payload: McpAuthToolInput) -> str:
        return payload.server

    def execute(self, payload: McpAuthToolInput, context: ToolContext) -> ToolExecutionResult:
        manager = context.metadata.get("mcp_manager")
        if not isinstance(manager, McpConnectionManager):
            raise ToolExecutionError("MCP manager is not configured.")
        known_servers = {state.server_name for state in manager.server_states()}
        if payload.server not in known_servers:
            raise ToolExecutionError(f"Unknown MCP server '{payload.server}'.")
        message = manager.auth_hint(payload.server)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=message,
            structured_output={"server": payload.server, "status": "manual", "hint": message},
        )
