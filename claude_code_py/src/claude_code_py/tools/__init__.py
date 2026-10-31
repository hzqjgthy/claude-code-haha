"""Tool implementations and registry."""

from collections.abc import Iterable

from claude_code_py.tools.registry import ToolRegistry


def build_default_tool_registry(
    *,
    extra_tools: Iterable | None = None,
) -> ToolRegistry:
    from claude_code_py.tools.agent import AgentTool
    from claude_code_py.tools.ask_user_question import AskUserQuestionTool
    from claude_code_py.tools.bash import BashTool
    from claude_code_py.tools.config import ConfigTool
    from claude_code_py.tools.file_edit import FileEditTool
    from claude_code_py.tools.file_read import FileReadTool
    from claude_code_py.tools.file_write import FileWriteTool
    from claude_code_py.tools.glob import GlobTool
    from claude_code_py.tools.grep import GrepTool
    from claude_code_py.tools.list_mcp_resources import ListMcpResourcesTool
    from claude_code_py.tools.mcp_auth import McpAuthTool
    from claude_code_py.tools.notebook_edit import NotebookEditTool
    from claude_code_py.tools.powershell import PowerShellTool
    from claude_code_py.tools.read_mcp_resource import ReadMcpResourceTool
    from claude_code_py.tools.send_message import SendMessageTool
    from claude_code_py.tools.skill import SkillTool
    from claude_code_py.tools.sleep import SleepTool
    from claude_code_py.tools.task_create import TaskCreateTool
    from claude_code_py.tools.task_get import TaskGetTool
    from claude_code_py.tools.task_list import TaskListTool
    from claude_code_py.tools.task_output import TaskOutputTool
    from claude_code_py.tools.task_stop import TaskStopTool
    from claude_code_py.tools.task_update import TaskUpdateTool
    from claude_code_py.tools.team_create import TeamCreateTool
    from claude_code_py.tools.team_delete import TeamDeleteTool
    from claude_code_py.tools.todo_write import TodoWriteTool
    from claude_code_py.tools.tool_search import ToolSearchTool
    from claude_code_py.tools.web_fetch import WebFetchTool
    from claude_code_py.tools.web_search import WebSearchTool
    from claude_code_py.tools.workflow import WorkflowTool

    tools = [
        BashTool(),
        FileReadTool(),
        FileEditTool(),
        FileWriteTool(),
        AgentTool(),
        GlobTool(),
        GrepTool(),
        WebFetchTool(),
        WebSearchTool(),
        PowerShellTool(),
        NotebookEditTool(),
        SleepTool(),
        SkillTool(),
        TodoWriteTool(),
        TaskCreateTool(),
        TaskGetTool(),
        TaskListTool(),
        TaskOutputTool(),
        TaskStopTool(),
        TaskUpdateTool(),
        TeamCreateTool(),
        TeamDeleteTool(),
        SendMessageTool(),
        ListMcpResourcesTool(),
        ReadMcpResourceTool(),
        McpAuthTool(),
        ToolSearchTool(),
        ConfigTool(),
        AskUserQuestionTool(),
        WorkflowTool(),
    ]
    if extra_tools is not None:
        tools.extend(extra_tools)
    return ToolRegistry(tools=tools)


__all__ = ["build_default_tool_registry", "ToolRegistry"]
