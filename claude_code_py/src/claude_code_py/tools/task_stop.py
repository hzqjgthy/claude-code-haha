from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_task_service
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class TaskStopToolInput(BaseModel):
    task_id: str


class TaskStopTool(BaseTool[TaskStopToolInput]):
    name = "TaskStop"
    description = "Stop a background task."
    input_model = TaskStopToolInput
    read_only = False
    destructive = True

    def summarize(self, payload: TaskStopToolInput) -> str:
        return payload.task_id

    def execute(self, payload: TaskStopToolInput, context: ToolContext) -> ToolExecutionResult:
        try:
            task = get_task_service(context).cancel_task(payload.task_id)
        except RuntimeError as exc:
            raise ToolExecutionError(str(exc)) from exc
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=f"Stopped task {task.task_id}.",
            structured_output=task.model_dump(mode="json"),
        )
