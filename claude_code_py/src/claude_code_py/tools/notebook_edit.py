from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from claude_code_py.domain.permissions import PermissionPromptRequest, PermissionTarget
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.tools.permission_preview import (
    build_unified_diff,
    clip_text,
    relativize_path,
)


class NotebookEditToolInput(BaseModel):
    notebook_path: str
    cell_id: str | None = None
    new_source: str = ""
    cell_type: str | None = None
    edit_mode: str = "replace"


class NotebookEditTool(BaseTool[NotebookEditToolInput]):
    name = "NotebookEdit"
    description = "Edit a Jupyter notebook cell."
    input_model = NotebookEditToolInput
    read_only = False
    destructive = True

    def validate(self, payload: NotebookEditToolInput, context: ToolContext) -> None:
        path = context.resolve_path(payload.notebook_path)
        if path.suffix != ".ipynb":
            raise ToolExecutionError("notebook_path must point to a .ipynb file.")
        if not path.exists():
            raise ToolExecutionError(f"Notebook not found: {path}")
        if payload.edit_mode not in {"replace", "insert", "delete"}:
            raise ToolExecutionError("edit_mode must be replace, insert, or delete.")
        if payload.edit_mode in {"replace", "delete"} and not payload.cell_id:
            raise ToolExecutionError("cell_id is required for replace and delete.")
        if payload.edit_mode == "insert" and payload.cell_type not in {"code", "markdown"}:
            raise ToolExecutionError("cell_type is required for insert and must be code or markdown.")

    def summarize(self, payload: NotebookEditToolInput) -> str:
        return payload.notebook_path

    def permission_targets(
        self,
        payload: NotebookEditToolInput,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        path = context.resolve_path(payload.notebook_path)
        return [
            PermissionTarget(tool_name=self.name),
            PermissionTarget(tool_name=self.name, kind="path", value=str(path)),
        ]

    def build_permission_request(
        self,
        payload: NotebookEditToolInput,
        context: ToolContext,
        *,
        summary: str,
        reason: str | None,
    ) -> PermissionPromptRequest:
        path = context.resolve_path(payload.notebook_path)
        notebook = __import__("json").loads(path.read_text(encoding="utf-8"))
        cells = notebook.get("cells") or []
        current_source = ""
        current_cell_type = payload.cell_type or ""
        if payload.cell_id is not None:
            for index, cell in enumerate(cells):
                if isinstance(cell, dict) and _cell_identity(cell, index) == payload.cell_id:
                    source = cell.get("source") or []
                    if isinstance(source, list):
                        current_source = "".join(str(item) for item in source)
                    else:
                        current_source = str(source)
                    current_cell_type = str(cell.get("cell_type") or current_cell_type)
                    break

        if payload.edit_mode == "replace":
            preview = build_unified_diff(
                current_source,
                payload.new_source,
                fromfile="before-cell",
                tofile="after-cell",
            )
        elif payload.edit_mode == "delete":
            preview = clip_text(current_source, max_lines=30, max_chars=2500)
        else:
            preview = clip_text(payload.new_source, max_lines=30, max_chars=2500)

        return PermissionPromptRequest(
            tool_name=self.name,
            summary=summary,
            reason=reason,
            targets=self.permission_targets(payload, context),
            request_kind="notebook_edit",
            title="Edit notebook",
            subtitle=relativize_path(path, context.workspace_root),
            prompt="Do you want to apply this notebook edit?",
            detail_lines=[
                f"path: {path}",
                f"edit_mode: {payload.edit_mode}",
                f"cell_id: {payload.cell_id or '(new cell)'}",
                f"cell_type: {payload.cell_type or current_cell_type or '(unchanged)'}",
            ],
            preview=preview,
            metadata={
                "notebook_path": str(path),
                "edit_mode": payload.edit_mode,
                "cell_id": payload.cell_id,
            },
        )

    def history_paths(
        self,
        payload: NotebookEditToolInput,
        context: ToolContext,
    ) -> list[Path]:
        return [context.resolve_path(payload.notebook_path)]

    def execute(self, payload: NotebookEditToolInput, context: ToolContext) -> ToolExecutionResult:
        path = context.resolve_path(payload.notebook_path)
        notebook = __import__("json").loads(path.read_text(encoding="utf-8"))
        cells = notebook.get("cells")
        if not isinstance(cells, list):
            raise ToolExecutionError("Notebook does not contain a valid cells array.")

        def cell_identity(cell: dict, index: int) -> str:
            value = cell.get("id")
            return str(value) if isinstance(value, str) else str(index)

        target_index = None
        if payload.cell_id is not None:
            for index, cell in enumerate(cells):
                if isinstance(cell, dict) and cell_identity(cell, index) == payload.cell_id:
                    target_index = index
                    break
            if target_index is None and payload.edit_mode != "insert":
                raise ToolExecutionError(f"Cell '{payload.cell_id}' was not found.")

        source = payload.new_source.splitlines(keepends=True)
        if payload.edit_mode == "replace":
            assert target_index is not None
            cell = dict(cells[target_index])
            cell["source"] = source
            if payload.cell_type in {"code", "markdown"}:
                cell["cell_type"] = payload.cell_type
            cells[target_index] = cell
            result_text = f"Updated cell {payload.cell_id}"
            result_cell_id = payload.cell_id
        elif payload.edit_mode == "insert":
            insert_index = 0 if target_index is None else target_index + 1
            new_id = uuid4().hex[:8]
            new_cell = {
                "cell_type": payload.cell_type,
                "metadata": {},
                "source": source,
                "id": new_id,
            }
            if payload.cell_type == "code":
                new_cell["outputs"] = []
                new_cell["execution_count"] = None
            cells.insert(insert_index, new_cell)
            result_text = f"Inserted cell {new_id}"
            result_cell_id = new_id
        else:
            assert target_index is not None
            cells.pop(target_index)
            result_text = f"Deleted cell {payload.cell_id}"
            result_cell_id = payload.cell_id

        notebook["cells"] = cells
        path.write_text(
            __import__("json").dumps(notebook, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=result_text,
            structured_output={
                "notebook_path": str(path),
                "cell_id": result_cell_id,
                "edit_mode": payload.edit_mode,
                "cell_type": payload.cell_type,
                "new_source": payload.new_source,
            },
        )


def _cell_identity(cell: dict, index: int) -> str:
    value = cell.get("id")
    return str(value) if isinstance(value, str) else str(index)
