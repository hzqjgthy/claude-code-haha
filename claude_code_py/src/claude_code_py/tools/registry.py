from collections.abc import Iterable

from claude_code_py.tools.base import BaseTool


class ToolRegistry:
    def __init__(self, tools: Iterable[BaseTool] | None = None) -> None:
        self._tools: dict[str, BaseTool] = {}
        if tools is not None:
            for tool in tools:
                self.register(tool)

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, tool_name: str) -> BaseTool:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            known = ", ".join(sorted(self._tools))
            raise KeyError(f"Unknown tool '{tool_name}'. Known tools: {known}") from exc

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())
