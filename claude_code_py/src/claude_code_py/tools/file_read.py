from pydantic import BaseModel, Field

from claude_code_py.domain.permissions import PermissionTarget
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.tools.file_context import remember_file_context_path


class FileReadToolInput(BaseModel):
    file_path: str
    offset: int = 0
    limit: int | None = None


class FileReadTool(BaseTool[FileReadToolInput]):
    name = "Read"
    description = "Read a text file from the local workspace."
    input_model = FileReadToolInput
    read_only = True
    destructive = False

    def validate(self, payload: FileReadToolInput, context: ToolContext) -> None:
        file_path = context.resolve_path(payload.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if payload.offset < 0:
            raise ToolExecutionError("offset must be >= 0")
        if payload.limit is not None and payload.limit < 0:
            raise ToolExecutionError("limit must be >= 0")

    def summarize(self, payload: FileReadToolInput) -> str:
        return payload.file_path

    def permission_targets(
        self,
        payload: FileReadToolInput,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        file_path = context.resolve_path(payload.file_path)
        return [
            PermissionTarget(tool_name=self.name),
            PermissionTarget(tool_name=self.name, kind="path", value=str(file_path)),
        ]

    def execute(self, payload: FileReadToolInput, context: ToolContext) -> ToolExecutionResult:
        file_path = context.resolve_path(payload.file_path)
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        sliced = lines[payload.offset :]
        if payload.limit is not None:
            sliced = sliced[: payload.limit]
        rendered = "\n".join(sliced)
        remember_file_context_path(context, file_path)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=rendered,
            structured_output={
                "file_path": str(file_path),
                "offset": payload.offset,
                "limit": payload.limit,
                "line_count": len(sliced),
            },
        )
