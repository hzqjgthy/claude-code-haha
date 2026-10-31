from pathlib import Path

from pydantic import BaseModel

from claude_code_py.domain.permissions import PermissionPromptRequest, PermissionTarget
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.tools.file_context import remember_file_context_path
from claude_code_py.tools.permission_preview import (
    build_unified_diff,
    clip_text,
    relativize_path,
    safe_read_text,
)


class FileWriteToolInput(BaseModel):
    file_path: str
    content: str


class FileWriteTool(BaseTool[FileWriteToolInput]):
    name = "Write"
    description = "Create or overwrite a file in the local workspace."
    input_model = FileWriteToolInput
    read_only = False
    destructive = True

    def validate(self, payload: FileWriteToolInput, context: ToolContext) -> None:
        del context
        if not payload.file_path.strip():
            raise ToolExecutionError("file_path cannot be empty.")

    def summarize(self, payload: FileWriteToolInput) -> str:
        return payload.file_path

    def permission_targets(
        self,
        payload: FileWriteToolInput,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        file_path = context.resolve_path(payload.file_path)
        return [
            PermissionTarget(tool_name=self.name),
            PermissionTarget(tool_name=self.name, kind="path", value=str(file_path)),
        ]

    def build_permission_request(
        self,
        payload: FileWriteToolInput,
        context: ToolContext,
        *,
        summary: str,
        reason: str | None,
    ) -> PermissionPromptRequest:
        file_path = context.resolve_path(payload.file_path)
        existing = safe_read_text(file_path) if file_path.exists() else ""
        preview = (
            build_unified_diff(
                existing or "",
                payload.content,
                fromfile=f"a/{relativize_path(file_path, context.workspace_root)}",
                tofile=f"b/{relativize_path(file_path, context.workspace_root)}",
            )
            if existing is not None
            else clip_text(payload.content)
        )
        exists = file_path.exists()
        return PermissionPromptRequest(
            tool_name=self.name,
            summary=summary,
            reason=reason,
            targets=self.permission_targets(payload, context),
            request_kind="file_write",
            title="Overwrite file" if exists else "Create file",
            subtitle=relativize_path(file_path, context.workspace_root),
            prompt=(
                "Do you want to overwrite this file?"
                if exists
                else "Do you want to create this file?"
            ),
            detail_lines=[
                f"path: {file_path}",
                f"operation: {'overwrite' if exists else 'create'}",
                f"content_chars: {len(payload.content)}",
            ],
            preview=preview,
            metadata={"file_path": str(file_path), "operation": "overwrite" if exists else "create"},
        )

    def history_paths(
        self,
        payload: FileWriteToolInput,
        context: ToolContext,
    ) -> list[Path]:
        return [context.resolve_path(payload.file_path)]

    def execute(self, payload: FileWriteToolInput, context: ToolContext) -> ToolExecutionResult:
        file_path = context.resolve_path(payload.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        existed = file_path.exists()
        file_path.write_text(payload.content, encoding="utf-8")
        operation = "update" if existed else "create"
        remember_file_context_path(context, file_path)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=f"Wrote {len(payload.content)} characters to {file_path}.",
            structured_output={
                "file_path": str(file_path),
                "operation": operation,
                "content": payload.content,
            },
        )
