from pathlib import Path

from pydantic import BaseModel, Field

from claude_code_py.domain.permissions import (
    PermissionDecision,
    PermissionPromptRequest,
    PermissionTarget,
)
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.tools.permission_preview import clip_text, relativize_path


class BashToolInput(BaseModel):
    command: str
    timeout: int | None = None
    cwd: str | None = None


class BashTool(BaseTool[BashToolInput]):
    name = "Bash"
    description = "Run a shell command inside the workspace."
    input_model = BashToolInput
    read_only = False
    destructive = True

    def validate(self, payload: BashToolInput, context: ToolContext) -> None:
        del context
        if not payload.command.strip():
            raise ToolExecutionError("Bash command cannot be empty.")

    def summarize(self, payload: BashToolInput) -> str:
        command = payload.command.strip()
        return command[:80] if command else "Bash invocation"

    def permission_targets(
        self,
        payload: BashToolInput,
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
        payload: BashToolInput,
        context: ToolContext,
    ) -> PermissionDecision:
        prefs = _runtime_preferences(context)
        if prefs is None or not prefs.sandbox_enabled:
            return PermissionDecision(behavior="allow")
        if prefs.sandbox_allow_unsandboxed_fallback:
            return PermissionDecision(behavior="allow")
        return PermissionDecision(
            behavior="ask",
            reason=(
                "Sandbox is enabled, but this Python refactor does not yet run "
                "Bash commands inside an enforced sandbox. Approval is required "
                "before running the command unsandboxed."
            ),
        )

    def build_permission_request(
        self,
        payload: BashToolInput,
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
                "sandbox: enabled, command will run via unsandboxed fallback"
            )
        return PermissionPromptRequest(
            tool_name=self.name,
            summary=summary,
            reason=reason,
            targets=self.permission_targets(payload, context),
            request_kind="bash",
            title="Bash command",
            subtitle=relativize_path(cwd, context.workspace_root),
            prompt="Do you want to allow Claude to run this Bash command?",
            detail_lines=detail_lines,
            preview=clip_text(payload.command.strip(), max_lines=24, max_chars=2500),
            metadata={"command": payload.command, "cwd": str(cwd)},
        )

    def execute(self, payload: BashToolInput, context: ToolContext) -> ToolExecutionResult:
        if context.shell_provider is None:
            raise ToolExecutionError("No shell provider configured for Bash tool.")

        command_cwd = context.resolve_cwd(payload.cwd)
        shell_result = context.shell_provider.run(
            payload.command,
            cwd=command_cwd,
            timeout=payload.timeout,
        )
        parts = [part.strip() for part in [shell_result.stdout, shell_result.stderr] if part.strip()]
        output = "\n".join(parts).strip()
        if not output:
            output = "Done."

        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            is_error=shell_result.exit_code != 0 or shell_result.timed_out,
            structured_output={
                "command": shell_result.command,
                "cwd": str(shell_result.cwd),
                "exit_code": shell_result.exit_code,
                "stdout": shell_result.stdout,
                "stderr": shell_result.stderr,
                "timed_out": shell_result.timed_out,
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
