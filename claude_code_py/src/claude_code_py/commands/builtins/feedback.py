from datetime import UTC, datetime

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_feedback_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        report = invocation.args.strip()
        if not report:
            return CommandResult(
                kind="error",
                message="Usage: /feedback <report> or /bug <report>",
            )
        log_path = context.container.paths.data_dir / "feedback.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).isoformat(timespec="seconds")
        log_path.write_text(
            (
                log_path.read_text(encoding="utf-8")
                if log_path.exists()
                else ""
            )
            + f"[{timestamp}] {report}\n",
            encoding="utf-8",
        )
        return CommandResult(
            kind="message",
            message=f"Recorded feedback in {log_path}.",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="feedback",
            description="Submit feedback about Claude Code.",
            command_type="local_ui",
            argument_hint="[report]",
            aliases=["bug"],
        ),
        usage="/feedback [report]",
        handler=handler,
    )
