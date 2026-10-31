from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.providers.mcp import McpConnectionManager
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.domain.tools import ToolExecutionResult


class ListMcpResourcesToolInput(BaseModel):
    server: str | None = None


class ListMcpResourcesTool(BaseTool[ListMcpResourcesToolInput]):
    name = "ListMcpResourcesTool"
    description = "List available resources from configured MCP servers."
    input_model = ListMcpResourcesToolInput
    read_only = True
    destructive = False

    def execute(self, payload: ListMcpResourcesToolInput, context: ToolContext) -> ToolExecutionResult:
        manager = context.metadata.get("mcp_manager")
        if not isinstance(manager, McpConnectionManager):
            raise ToolExecutionError("MCP manager is not configured.")
        resources = manager.list_resources(payload.server)
        output = (
            "\n".join(
                f"{resource.server_name} | {resource.uri} | {resource.name or '(unnamed)'}"
                for resource in resources
            )
            if resources
            else "No MCP resources found"
        )
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            structured_output={
                "resources": [resource.model_dump(mode="json") for resource in resources],
            },
        )
