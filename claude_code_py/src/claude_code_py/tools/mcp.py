from typing import Any

from pydantic import BaseModel, ConfigDict

from claude_code_py.domain.permissions import PermissionTarget
from claude_code_py.domain.tools import ToolExecutionResult, ToolSpec
from claude_code_py.providers.mcp import McpConnectionManager, McpToolDefinition
from claude_code_py.tools.base import BaseTool, ToolContext


class McpToolInput(BaseModel):
    model_config = ConfigDict(extra="allow")


class McpTool(BaseTool[McpToolInput]):
    input_model = McpToolInput
    read_only = False
    destructive = False

    def __init__(
        self,
        *,
        definition: McpToolDefinition,
        manager: McpConnectionManager,
    ) -> None:
        self._definition = definition
        self._manager = manager
        self.name = definition.qualified_name
        self.description = definition.description or (
            f"MCP tool {definition.tool_name} from {definition.server_name}"
        )

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            read_only=self.read_only,
            destructive=self.destructive,
            input_schema=self._definition.input_schema,
        )

    def summarize(self, payload: McpToolInput) -> str:
        arguments = payload.model_dump(mode="json")
        if not arguments:
            return self.name
        first_key = next(iter(arguments))
        return f"{self.name} {first_key}"

    def permission_targets(
        self,
        payload: McpToolInput,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        del payload, context
        return [
            PermissionTarget(tool_name=self.name),
            PermissionTarget(
                tool_name=self.name,
                kind="command",
                value=self._definition.server_name,
            ),
        ]

    def execute(self, payload: McpToolInput, context: ToolContext) -> ToolExecutionResult:
        del context
        arguments = payload.model_dump(mode="json")
        result = self._manager.call_tool(
            self._definition.server_name,
            self._definition.tool_name,
            arguments,
        )
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=result.output,
            is_error=result.is_error,
            structured_output=result.raw_result,
        )
