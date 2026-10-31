from pathlib import Path

from pydantic import BaseModel

from claude_code_py.domain.permissions import PermissionPromptRequest, PermissionTarget
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.tools.file_context import remember_file_context_path
from claude_code_py.tools.permission_preview import (
    build_unified_diff,
    relativize_path,
)


class FileEditToolInput(BaseModel):
    file_path: str
    old_string: str
    new_string: str
    replace_all: bool = False


class FileEditTool(BaseTool[FileEditToolInput]):
    name = "Edit"
    description = "Replace text inside an existing file."
    input_model = FileEditToolInput
    read_only = False
    destructive = True

    def validate(self, payload: FileEditToolInput, context: ToolContext) -> None:
        file_path = context.resolve_path(payload.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if payload.old_string == payload.new_string:
            raise ToolExecutionError("old_string and new_string must be different.")

    def summarize(self, payload: FileEditToolInput) -> str:
        return payload.file_path

    def permission_targets(
        self,
        payload: FileEditToolInput,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        file_path = context.resolve_path(payload.file_path)
        return [
            PermissionTarget(tool_name=self.name),
            PermissionTarget(tool_name=self.name, kind="path", value=str(file_path)),
        ]

    def build_permission_request(
        self,
        payload: FileEditToolInput,
        context: ToolContext,
        *,
        summary: str,
        reason: str | None,
    ) -> PermissionPromptRequest:
        file_path = context.resolve_path(payload.file_path)
        original = file_path.read_text(encoding="utf-8")
        updated = (
            original.replace(payload.old_string, payload.new_string)
            if payload.replace_all
            else original.replace(payload.old_string, payload.new_string, 1)
        )
        replacements = (
            original.count(payload.old_string) if payload.replace_all else 1
        )
        preview = build_unified_diff(
            original,
            updated,
            fromfile=f"a/{relativize_path(file_path, context.workspace_root)}",
            tofile=f"b/{relativize_path(file_path, context.workspace_root)}",
        )
        return PermissionPromptRequest(
            tool_name=self.name,
            summary=summary,
            reason=reason,
            targets=self.permission_targets(payload, context),
            request_kind="file_edit",
            title="Edit file",
            subtitle=relativize_path(file_path, context.workspace_root),
            prompt="Do you want to apply this edit?",
            detail_lines=[
                f"path: {file_path}",
                f"replace_all: {payload.replace_all}",
                f"planned_replacements: {replacements}",
            ],
            preview=preview,
            metadata={
                "file_path": str(file_path),
                "replace_all": payload.replace_all,
                "planned_replacements": replacements,
            },
        )

    def history_paths(
        self,
        payload: FileEditToolInput,
        context: ToolContext,
    ) -> list[Path]:
        return [context.resolve_path(payload.file_path)]

    def execute(self, payload: FileEditToolInput, context: ToolContext) -> ToolExecutionResult:
        file_path = context.resolve_path(payload.file_path)
        original = file_path.read_text(encoding="utf-8")
        if payload.old_string not in original:
            raise ToolExecutionError(
                f"String not found in file: {payload.old_string!r}",
            )

        if payload.replace_all:
            updated = original.replace(payload.old_string, payload.new_string)
            replacements = original.count(payload.old_string)
        else:
            updated = original.replace(payload.old_string, payload.new_string, 1)
            replacements = 1

        file_path.write_text(updated, encoding="utf-8")
        remember_file_context_path(context, file_path)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=f"Updated {file_path} with {replacements} replacement(s).",
            structured_output={
                "file_path": str(file_path),
                "replacements": replacements,
                "replace_all": payload.replace_all,
            },
        )
