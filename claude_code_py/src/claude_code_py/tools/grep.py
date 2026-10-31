from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel

from claude_code_py.domain.permissions import PermissionTarget
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import relativize_path
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError

DEFAULT_GREP_LIMIT = 250


class GrepToolInput(BaseModel):
    pattern: str
    path: str | None = None
    glob: str | None = None
    output_mode: str = "files_with_matches"
    case_insensitive: bool = False
    head_limit: int = DEFAULT_GREP_LIMIT
    offset: int = 0


class GrepTool(BaseTool[GrepToolInput]):
    name = "Grep"
    description = "Search file contents with a regular expression."
    input_model = GrepToolInput
    read_only = True
    destructive = False

    def validate(self, payload: GrepToolInput, context: ToolContext) -> None:
        if not payload.pattern.strip():
            raise ToolExecutionError("pattern cannot be empty.")
        if payload.output_mode not in {"content", "files_with_matches", "count"}:
            raise ToolExecutionError(
                "output_mode must be content, files_with_matches, or count.",
            )
        if payload.head_limit < 0 or payload.offset < 0:
            raise ToolExecutionError("head_limit and offset must be >= 0.")
        if payload.path:
            search_path = context.resolve_path(payload.path)
            if not search_path.exists():
                raise ToolExecutionError(f"Search path not found: {search_path}")
        re.compile(payload.pattern)

    def summarize(self, payload: GrepToolInput) -> str:
        return payload.pattern

    def permission_targets(
        self,
        payload: GrepToolInput,
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

    def execute(self, payload: GrepToolInput, context: ToolContext) -> ToolExecutionResult:
        search_path = context.resolve_path(payload.path) if payload.path else context.cwd
        started = perf_counter()
        if shutil.which("rg"):
            output, structured = self._run_ripgrep(payload, search_path, context.cwd)
        else:
            output, structured = self._run_python_grep(payload, search_path, context.cwd)
        structured["durationMs"] = int((perf_counter() - started) * 1000)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            structured_output=structured,
        )

    def _run_ripgrep(
        self,
        payload: GrepToolInput,
        search_path: Path,
        cwd: Path,
    ) -> tuple[str, dict[str, object]]:
        args = ["rg"]
        if payload.case_insensitive:
            args.append("-i")
        if payload.glob:
            args.extend(["--glob", payload.glob])
        if payload.output_mode == "files_with_matches":
            args.append("-l")
        elif payload.output_mode == "count":
            args.append("-c")
        else:
            args.append("-n")
        args.extend([payload.pattern, str(search_path)])
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode not in {0, 1}:
            raise ToolExecutionError(completed.stderr.strip() or "ripgrep failed.")
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        sliced = lines[payload.offset :]
        if payload.head_limit:
            sliced = sliced[: payload.head_limit]
        output = "\n".join(sliced) if sliced else "No matches found"
        return output, {
            "mode": payload.output_mode,
            "path": str(search_path),
            "pattern": payload.pattern,
            "numFiles": len(sliced) if payload.output_mode != "content" else None,
            "numLines": len(sliced) if payload.output_mode == "content" else None,
            "items": sliced,
        }

    def _run_python_grep(
        self,
        payload: GrepToolInput,
        search_path: Path,
        cwd: Path,
    ) -> tuple[str, dict[str, object]]:
        flags = re.IGNORECASE if payload.case_insensitive else 0
        regex = re.compile(payload.pattern, flags=flags)
        files = (
            [search_path]
            if search_path.is_file()
            else [path for path in search_path.rglob("*") if path.is_file()]
        )
        if payload.glob:
            files = [path for path in files if path.match(payload.glob)]

        matches: list[str] = []
        counts: list[str] = []
        file_hits: list[str] = []
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            local_count = 0
            for line_number, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    local_count += 1
                    if payload.output_mode == "content":
                        matches.append(
                            f"{relativize_path(path, cwd)}:{line_number}:{line}",
                        )
            if local_count:
                file_label = relativize_path(path, cwd)
                file_hits.append(file_label)
                if payload.output_mode == "count":
                    counts.append(f"{file_label}:{local_count}")

        items = (
            matches
            if payload.output_mode == "content"
            else counts
            if payload.output_mode == "count"
            else file_hits
        )
        sliced = items[payload.offset :]
        if payload.head_limit:
            sliced = sliced[: payload.head_limit]
        output = "\n".join(sliced) if sliced else "No matches found"
        return output, {
            "mode": payload.output_mode,
            "path": str(search_path),
            "pattern": payload.pattern,
            "numFiles": len(file_hits),
            "numLines": len(matches),
            "items": sliced,
        }
