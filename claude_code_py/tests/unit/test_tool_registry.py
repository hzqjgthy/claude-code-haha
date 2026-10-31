from claude_code_py.tools import build_default_tool_registry


def test_default_tool_registry_contains_core_tools() -> None:
    registry = build_default_tool_registry()

    names = [tool.name for tool in registry.list_tools()]

    assert names == [
        "Bash",
        "Read",
        "Edit",
        "Write",
        "Agent",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
        "PowerShell",
        "NotebookEdit",
        "Sleep",
        "Skill",
        "TodoWrite",
        "TaskCreate",
        "TaskGet",
        "TaskList",
        "TaskOutput",
        "TaskStop",
        "TaskUpdate",
        "TeamCreate",
        "TeamDelete",
        "SendMessage",
        "ListMcpResourcesTool",
        "ReadMcpResourceTool",
        "McpAuth",
        "ToolSearch",
        "Config",
        "AskUserQuestion",
        "workflow",
    ]
