from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_shared_state_bucket
from claude_code_py.tools.base import BaseTool, ToolContext


class TodoItem(BaseModel):
    content: str
    status: str = "pending"
    active_form: str | None = None


class TodoWriteToolInput(BaseModel):
    todos: list[TodoItem]


class TodoWriteTool(BaseTool[TodoWriteToolInput]):
    name = "TodoWrite"
    description = "Update the current session todo list."
    input_model = TodoWriteToolInput
    read_only = False
    destructive = False

    def summarize(self, payload: TodoWriteToolInput) -> str:
        return f"{len(payload.todos)} todo item(s)"

    def execute(self, payload: TodoWriteToolInput, context: ToolContext) -> ToolExecutionResult:
        session_id = str(context.metadata.get("session_id", "default"))
        bucket = get_shared_state_bucket(context, "session_todos")
        old_todos = list(bucket.get(session_id, []))
        new_todos = [
            item.model_dump(mode="json")
            for item in payload.todos
            if item.status != "completed"
        ]
        bucket[session_id] = new_todos
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=(
                f"Todo list updated successfully. Active items: {len(new_todos)}"
            ),
            structured_output={
                "oldTodos": old_todos,
                "newTodos": [item.model_dump(mode="json") for item in payload.todos],
            },
        )
