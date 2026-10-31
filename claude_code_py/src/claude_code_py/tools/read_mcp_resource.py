from __future__ import annotations

import json

from pydantic import BaseModel

from claude_code_py.providers.mcp import McpConnectionManager
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.domain.tools import ToolExecutionResult


class ReadMcpResourceToolInput(BaseModel):
    server: str
    uri: str


class ReadMcpResourceTool(BaseTool[ReadMcpResourceToolInput]):
    name = "ReadMcpResourceTool"
    description = "Read a specific resource from an MCP server."
    input_model = ReadMcpResourceToolInput
    read_only = True
    destructive = False

    def summarize(self, payload: ReadMcpResourceToolInput) -> str:
        return f"{payload.server}:{payload.uri}"

    def execute(self, payload: ReadMcpResourceToolInput, context: ToolContext) -> ToolExecutionResult:
        manager = context.metadata.get("mcp_manager")
        if not isinstance(manager, McpConnectionManager):
            raise ToolExecutionError("MCP manager is not configured.")
        result = manager.read_resource(payload.server, payload.uri)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            structured_output=result,
        )
