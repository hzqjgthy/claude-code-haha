from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_task_service
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class TaskGetToolInput(BaseModel):
    task_id: str


class TaskGetTool(BaseTool[TaskGetToolInput]):
    name = "TaskGet"
    description = "Retrieve a task by ID."
    input_model = TaskGetToolInput
    read_only = True
    destructive = False

    def summarize(self, payload: TaskGetToolInput) -> str:
        return payload.task_id

    def execute(self, payload: TaskGetToolInput, context: ToolContext) -> ToolExecutionResult:
        task = get_task_service(context).get_task(payload.task_id)
        if task is None:
            raise ToolExecutionError(f"Task '{payload.task_id}' was not found.")
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output="\n".join(
                [
                    f"task_id: {task.task_id}",
                    f"kind: {task.kind}",
                    f"status: {task.status}",
                    f"background: {task.background}",
                    f"owner: {task.owner or '(none)'}",
                    f"description: {task.description}",
                    f"prompt: {task.prompt}",
                ]
            ),
            structured_output=task.model_dump(mode="json"),
        )
