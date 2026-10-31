from __future__ import annotations

import shutil
import subprocess

from pydantic import BaseModel

from claude_code_py.domain.permissions import (
    PermissionDecision,
    PermissionPromptRequest,
    PermissionTarget,
)
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.tools.permission_preview import clip_text, relativize_path


class PowerShellToolInput(BaseModel):
    command: str
    timeout: int | None = None
    cwd: str | None = None


class PowerShellTool(BaseTool[PowerShellToolInput]):
    name = "PowerShell"
    description = "Run a PowerShell command."
    input_model = PowerShellToolInput
    read_only = False
    destructive = True

    def validate(self, payload: PowerShellToolInput, context: ToolContext) -> None:
        del context
        if not payload.command.strip():
            raise ToolExecutionError("PowerShell command cannot be empty.")

    def summarize(self, payload: PowerShellToolInput) -> str:
        command = payload.command.strip()
        return command[:80] if command else "PowerShell invocation"

    def permission_targets(
        self,
        payload: PowerShellToolInput,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        del context
        command = payload.command.strip()
        first_token = command.split(maxsplit=1)[0] if command else ""
        return [
            PermissionTarget(tool_name=self.name),
            PermissionTarget(tool_name=self.name, kind="command", value=command),
            PermissionTarget(
                tool_name=self.name,
                kind="command_prefix",
                value=first_token,
            ),
        ]

    def check_permissions(
        self,
        payload: PowerShellToolInput,
        context: ToolContext,
    ) -> PermissionDecision:
        del payload
        prefs = _runtime_preferences(context)
        if prefs is None or not prefs.sandbox_enabled:
            return PermissionDecision(behavior="allow")
        if prefs.sandbox_allow_unsandboxed_fallback:
            return PermissionDecision(behavior="allow")
        return PermissionDecision(
            behavior="ask",
            reason=(
                "Sandbox is enabled, but PowerShell commands currently run "
                "outside an enforced sandbox in the Python refactor. Approval "
                "is required before using the unsandboxed fallback."
            ),
        )

    def build_permission_request(
        self,
        payload: PowerShellToolInput,
        context: ToolContext,
        *,
        summary: str,
        reason: str | None,
    ) -> PermissionPromptRequest:
        cwd = context.resolve_cwd(payload.cwd)
        detail_lines = [
            f"cwd: {relativize_path(cwd, context.workspace_root)}",
        ]
        prefs = _runtime_preferences(context)
        if prefs is not None and prefs.sandbox_enabled:
            detail_lines.append(
                "sandbox: enabled, PowerShell will run via unsandboxed fallback"
            )
        return PermissionPromptRequest(
            tool_name=self.name,
            summary=summary,
            reason=reason,
            targets=self.permission_targets(payload, context),
            request_kind="powershell",
            title="PowerShell command",
            subtitle=relativize_path(cwd, context.workspace_root),
            prompt="Do you want to allow Claude to run this PowerShell command?",
            detail_lines=detail_lines,
            preview=clip_text(payload.command.strip(), max_lines=24, max_chars=2500),
            metadata={"command": payload.command, "cwd": str(cwd)},
        )

    def execute(self, payload: PowerShellToolInput, context: ToolContext) -> ToolExecutionResult:
        executable = shutil.which("pwsh") or shutil.which("powershell")
        if executable is None:
            raise ToolExecutionError("PowerShell executable was not found.")
        cwd = context.resolve_cwd(payload.cwd)
        completed = subprocess.run(
            [executable, "-NoProfile", "-Command", payload.command],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=payload.timeout,
            check=False,
        )
        parts = [
            part.strip()
            for part in [completed.stdout, completed.stderr]
            if part.strip()
        ]
        output = "\n".join(parts) if parts else "Done."
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            is_error=completed.returncode != 0,
            structured_output={
                "command": payload.command,
                "cwd": str(cwd),
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )


def _runtime_preferences(context: ToolContext):
    store = context.metadata.get("runtime_state_store")
    if store is None:
        return None
    getter = getattr(store, "get_preferences", None)
    if not callable(getter):
        return None
    return getter()
