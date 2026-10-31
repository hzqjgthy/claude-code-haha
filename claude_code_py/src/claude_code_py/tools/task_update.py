from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_task_service
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class TaskUpdateToolInput(BaseModel):
    task_id: str
    description: str | None = None
    prompt: str | None = None
    status: str | None = None
    model: str | None = None
    owner: str | None = None


class TaskUpdateTool(BaseTool[TaskUpdateToolInput]):
    name = "TaskUpdate"
    description = "Update a task."
    input_model = TaskUpdateToolInput
    read_only = False
    destructive = False

    def summarize(self, payload: TaskUpdateToolInput) -> str:
        return payload.task_id

    def execute(self, payload: TaskUpdateToolInput, context: ToolContext) -> ToolExecutionResult:
        service = get_task_service(context)
        if payload.status == "cancelled":
            try:
                task = service.cancel_task(payload.task_id)
            except RuntimeError as exc:
                raise ToolExecutionError(str(exc)) from exc
        else:
            changes = {}
            if payload.description is not None:
                changes["description"] = payload.description
            if payload.prompt is not None:
                changes["prompt"] = payload.prompt
            if payload.status is not None:
                changes["status"] = payload.status
            if payload.model is not None:
                changes["model"] = payload.model
            if payload.owner is not None:
                changes["owner"] = payload.owner
            if not changes:
                raise ToolExecutionError("No task fields were provided to update.")
            task = service.update_task(payload.task_id, **changes)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=f"Updated task {task.task_id}.",
            structured_output=task.model_dump(mode="json"),
        )
