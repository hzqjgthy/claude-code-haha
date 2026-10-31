from __future__ import annotations

from glob import glob
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel

from claude_code_py.domain.permissions import PermissionTarget
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import relativize_path
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError

DEFAULT_GLOB_LIMIT = 100


class GlobToolInput(BaseModel):
    pattern: str
    path: str | None = None
    limit: int = DEFAULT_GLOB_LIMIT


class GlobTool(BaseTool[GlobToolInput]):
    name = "Glob"
    description = "Find files by glob pattern."
    input_model = GlobToolInput
    read_only = True
    destructive = False

    def validate(self, payload: GlobToolInput, context: ToolContext) -> None:
        if not payload.pattern.strip():
            raise ToolExecutionError("pattern cannot be empty.")
        if payload.limit <= 0:
            raise ToolExecutionError("limit must be > 0.")
        if payload.path:
            base = context.resolve_path(payload.path)
            if not base.exists() or not base.is_dir():
                raise ToolExecutionError(f"Search directory not found: {base}")

    def summarize(self, payload: GlobToolInput) -> str:
        return payload.pattern

    def permission_targets(
        self,
        payload: GlobToolInput,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        targets = [PermissionTarget(tool_name=self.name)]
        if payload.path:
            targets.append(
                PermissionTarget(
                    tool_name=self.name,
                    kind="path",
                    value=str(context.resolve_path(payload.path)),
                ),
            )
        return targets

    def execute(self, payload: GlobToolInput, context: ToolContext) -> ToolExecutionResult:
        base = context.resolve_path(payload.path) if payload.path else context.cwd
        started = perf_counter()
        matches = sorted(
            Path(path).resolve()
            for path in glob(str(base / payload.pattern), recursive=True)
        )
        matches = [path for path in matches if path.is_file()]
        truncated = len(matches) > payload.limit
        selected = matches[: payload.limit]
        rendered = [relativize_path(path, context.cwd) for path in selected]
        output = "\n".join(rendered) if rendered else "No files found"
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            structured_output={
                "path": str(base),
                "pattern": payload.pattern,
                "numFiles": len(rendered),
                "filenames": rendered,
                "truncated": truncated,
                "durationMs": int((perf_counter() - started) * 1000),
            },
        )
