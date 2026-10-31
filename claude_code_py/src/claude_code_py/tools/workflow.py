from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class WorkflowToolInput(BaseModel):
    workflow_name: str | None = None
    arguments: str | None = None


class WorkflowTool(BaseTool[WorkflowToolInput]):
    name = "workflow"
    description = "Inspect project workflow definitions."
    input_model = WorkflowToolInput
    read_only = True
    destructive = False

    def summarize(self, payload: WorkflowToolInput) -> str:
        return payload.workflow_name or "list workflows"

    def execute(self, payload: WorkflowToolInput, context: ToolContext) -> ToolExecutionResult:
        root = context.workspace_root / ".claude" / "workflows"
        files = sorted(root.rglob("*.md")) if root.exists() else []
        if payload.workflow_name is None:
            output = (
                "\n".join(path.stem for path in files)
                if files
                else "No workflows found"
            )
            return ToolExecutionResult(
                tool_name=self.name,
                tool_use_id=None,
                output=output,
                structured_output={"workflows": [path.stem for path in files]},
            )
        target = next(
            (path for path in files if path.stem == payload.workflow_name),
            None,
        )
        if target is None:
            raise ToolExecutionError(f"Workflow '{payload.workflow_name}' was not found.")
        content = target.read_text(encoding="utf-8")
        if payload.arguments:
            content = f"{content}\n\nArguments:\n{payload.arguments}"
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=content,
            structured_output={"workflow_name": payload.workflow_name, "path": str(target)},
        )
