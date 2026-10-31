from pydantic import BaseModel, Field

from claude_code_py.application.task_service import TaskService
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class AgentToolInput(BaseModel):
    description: str
    prompt: str
    model: str | None = None
    run_in_background: bool = False
    task_kind: str = "agent"
    owner: str | None = None


class AgentTool(BaseTool[AgentToolInput]):
    name = "Agent"
    description = "Launch an in-process sub-agent for a delegated task."
    input_model = AgentToolInput
    read_only = False
    destructive = False

    def validate(self, payload: AgentToolInput, context: ToolContext) -> None:
        del context
        if not payload.description.strip():
            raise ToolExecutionError("Agent description cannot be empty.")
        if not payload.prompt.strip():
            raise ToolExecutionError("Agent prompt cannot be empty.")

    def summarize(self, payload: AgentToolInput) -> str:
        return payload.description.strip()

    def execute(self, payload: AgentToolInput, context: ToolContext) -> ToolExecutionResult:
        task_service = context.metadata.get("task_service")
        if not isinstance(task_service, TaskService):
            raise ToolExecutionError("Task service is not configured.")

        history = context.metadata.get("conversation_history", [])
        if not isinstance(history, list):
            history = []
        model = payload.model or str(
            context.metadata.get("current_model", context.default_model),
        )
        system_prompt = context.metadata.get("system_prompt")
        if system_prompt is not None and not isinstance(system_prompt, str):
            system_prompt = None

        session_id = context.metadata.get("session_id")
        if session_id is not None and not isinstance(session_id, str):
            session_id = None
        parent_task_id = context.metadata.get("current_task_id")
        if parent_task_id is not None and not isinstance(parent_task_id, str):
            parent_task_id = None

        submission = task_service.submit_agent_task(
            description=payload.description.strip(),
            prompt=payload.prompt.strip(),
            history=history,
            model=model,
            system_prompt=system_prompt,
            session_id=session_id,
            background=payload.run_in_background,
            parent_task_id=parent_task_id,
            kind=payload.task_kind if payload.task_kind in {"agent", "teammate", "workflow", "plugin", "mcp"} else "agent",
            owner=payload.owner,
        )

        if payload.run_in_background:
            output = (
                f"Background task started.\n"
                f"task_id: {submission.task.task_id}\n"
                f"description: {submission.task.description}"
            )
            structured_output = submission.task.model_dump(mode="json")
        else:
            result = submission.result
            if result is None:
                raise ToolExecutionError("Synchronous agent run did not return a result.")
            output = result.text
            structured_output = {
                "task": submission.task.model_dump(mode="json"),
                "result": result.model_dump(mode="json"),
            }

        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            structured_output=structured_output,
        )
