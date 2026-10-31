from __future__ import annotations

from pydantic import BaseModel, Field

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_task_service
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class TaskOutputToolInput(BaseModel):
    task_id: str
    block: bool = True
    timeout_ms: int = Field(default=30_000, ge=0, le=600_000)


class TaskOutputTool(BaseTool[TaskOutputToolInput]):
    name = "TaskOutput"
    description = "Get output from a task."
    input_model = TaskOutputToolInput
    read_only = True
    destructive = False

    def summarize(self, payload: TaskOutputToolInput) -> str:
        return payload.task_id

    def execute(self, payload: TaskOutputToolInput, context: ToolContext) -> ToolExecutionResult:
        service = get_task_service(context)
        if payload.block:
            task = service.wait_for_task(payload.task_id, timeout=payload.timeout_ms / 1000)
        else:
            task = service.get_task(payload.task_id)
            if task is None:
                raise ToolExecutionError(f"Task '{payload.task_id}' was not found.")
        lines = [
            f"task_id: {task.task_id}",
            f"kind: {task.kind}",
            f"status: {task.status}",
            f"owner: {task.owner or '(none)'}",
            f"description: {task.description}",
        ]
        if task.result_text:
            lines.extend(["", task.result_text])
        if task.error_message:
            lines.extend(["", f"error: {task.error_message}"])
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output="\n".join(lines),
            structured_output=task.model_dump(mode="json"),
        )
