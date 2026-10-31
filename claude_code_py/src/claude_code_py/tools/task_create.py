from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_task_service
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class TaskCreateToolInput(BaseModel):
    description: str
    prompt: str
    model: str | None = None
    background: bool = True
    kind: str = "agent"
    owner: str | None = None


class TaskCreateTool(BaseTool[TaskCreateToolInput]):
    name = "TaskCreate"
    description = "Create a task backed by the Python task service."
    input_model = TaskCreateToolInput
    read_only = False
    destructive = False

    def validate(self, payload: TaskCreateToolInput, context: ToolContext) -> None:
        del context
        if not payload.description.strip():
            raise ToolExecutionError("description cannot be empty.")
        if not payload.prompt.strip():
            raise ToolExecutionError("prompt cannot be empty.")

    def summarize(self, payload: TaskCreateToolInput) -> str:
        return payload.description

    def execute(self, payload: TaskCreateToolInput, context: ToolContext) -> ToolExecutionResult:
        task_service = get_task_service(context)
        history = context.metadata.get("conversation_history", [])
        current_model = payload.model or str(
            context.metadata.get("current_model", context.default_model),
        )
        session_id = context.metadata.get("session_id")
        submission = task_service.submit_agent_task(
            description=payload.description.strip(),
            prompt=payload.prompt.strip(),
            history=history if isinstance(history, list) else [],
            model=current_model,
            system_prompt=(
                str(context.metadata.get("system_prompt"))
                if context.metadata.get("system_prompt") is not None
                else None
            ),
            session_id=session_id if isinstance(session_id, str) else None,
            background=payload.background,
            parent_task_id=(
                context.metadata.get("current_task_id")
                if isinstance(context.metadata.get("current_task_id"), str)
                else None
            ),
            kind=payload.kind if payload.kind in {"agent", "teammate", "workflow", "plugin", "mcp"} else "agent",
            owner=payload.owner,
        )
        if payload.background:
            output = (
                f"Task created.\n"
                f"task_id: {submission.task.task_id}\n"
                f"description: {submission.task.description}"
            )
        else:
            if submission.result is None:
                raise ToolExecutionError("Synchronous task did not return a result.")
            output = submission.result.text
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            structured_output={
                "task": submission.task.model_dump(mode="json"),
                "result": (
                    submission.result.model_dump(mode="json")
                    if submission.result is not None
                    else None
                ),
            },
        )
