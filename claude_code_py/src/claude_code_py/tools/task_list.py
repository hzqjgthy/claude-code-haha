from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_task_service
from claude_code_py.tools.base import BaseTool, ToolContext


class TaskListToolInput(BaseModel):
    pass


class TaskListTool(BaseTool[TaskListToolInput]):
    name = "TaskList"
    description = "List all known tasks."
    input_model = TaskListToolInput
    read_only = True
    destructive = False

    def execute(self, payload: TaskListToolInput, context: ToolContext) -> ToolExecutionResult:
        del payload
        tasks = get_task_service(context).list_tasks()
        output = (
            "\n".join(
                f"{task.task_id} | {task.kind} | {task.status} | bg={task.background} | {task.description}"
                for task in tasks
            )
            if tasks
            else "No tasks found"
        )
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            structured_output={
                "tasks": [task.model_dump(mode="json") for task in tasks],
            },
        )
