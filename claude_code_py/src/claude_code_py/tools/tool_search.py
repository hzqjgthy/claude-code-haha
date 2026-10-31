from __future__ import annotations

from pydantic import BaseModel, Field

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_tool_registry
from claude_code_py.tools.base import BaseTool, ToolContext


class ToolSearchToolInput(BaseModel):
    query: str
    max_results: int = Field(default=5, ge=1, le=20)


class ToolSearchTool(BaseTool[ToolSearchToolInput]):
    name = "ToolSearch"
    description = "Search available tools by name or description."
    input_model = ToolSearchToolInput
    read_only = True
    destructive = False

    def summarize(self, payload: ToolSearchToolInput) -> str:
        return payload.query

    def execute(self, payload: ToolSearchToolInput, context: ToolContext) -> ToolExecutionResult:
        registry = get_tool_registry(context)
        if registry is None:
            output = "No tool registry is attached to this runtime"
            return ToolExecutionResult(
                tool_name=self.name,
                tool_use_id=None,
                output=output,
                structured_output={
                    "matches": [],
                    "query": payload.query,
                    "total_deferred_tools": 0,
                },
            )
        query = payload.query.strip().lower()
        matches = []
        for tool in registry.list_tools():
            haystack = f"{tool.name} {tool.description}".lower()
            if query in haystack:
                matches.append(tool)
        selected = matches[: payload.max_results]
        output = (
            "\n".join(f"{tool.name} | {tool.description}" for tool in selected)
            if selected
            else "No matching tools found"
        )
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            structured_output={
                "matches": [tool.name for tool in selected],
                "query": payload.query,
                "total_deferred_tools": len(matches),
            },
        )
