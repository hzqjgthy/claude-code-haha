from pathlib import Path

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

PLAN_FILE_RELATIVE_PATH = Path(".claude_code_py") / "plan.md"


def build_plan_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        raw_args = invocation.args.strip()
        current_mode = context.permission_mode

        if current_mode != "plan":
            context.permission_service.set_mode("plan")
            context.permission_mode = context.permission_service.current_mode()
            context.bind_status()
            if raw_args and raw_args != "open":
                return CommandResult(kind="prompt", prompt=raw_args)
            return CommandResult(kind="message", message="Enabled plan mode.")

        plan_path = _plan_file_path(context)
        if raw_args == "open":
            return CommandResult(
                kind="message",
                message=(
                    "Plan editor integration is not implemented yet. "
                    f"Edit the plan manually at: {plan_path}"
                ),
            )

        if not plan_path.exists():
            return CommandResult(
                kind="message",
                message=(
                    "Already in plan mode. No plan written yet.\n"
                    f"Plan file: {plan_path}"
                ),
            )

        content = plan_path.read_text(encoding="utf-8").strip()
        if not content:
            return CommandResult(
                kind="message",
                message=(
                    "Already in plan mode. The current plan file is empty.\n"
                    f"Plan file: {plan_path}"
                ),
            )

        lines = [
            "Current plan:",
            f"path: {plan_path}",
            "",
            content,
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:plan",
            dialog_title="Plan",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="plan",
            description="Enable plan mode or inspect the current plan file.",
            command_type="local_ui",
            argument_hint="[request|open]",
        ),
        usage="/plan [request|open]",
        handler=handler,
    )


def _plan_file_path(context: CommandContext) -> Path:
    return (context.workspace_root / PLAN_FILE_RELATIVE_PATH).resolve()
