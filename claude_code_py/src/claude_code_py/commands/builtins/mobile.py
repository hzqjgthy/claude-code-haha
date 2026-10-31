from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_mobile_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        lines = [
            "Claude mobile app:",
            "iOS: https://apps.apple.com/app/claude-by-anthropic/id6473753684",
            "Android: https://play.google.com/store/apps/details?id=com.anthropic.claude",
            f"current_session_id: {context.session_state.metadata.session_id}",
            "Use the same Anthropic account on mobile to continue related work there.",
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:mobile",
            dialog_title="Mobile",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="mobile",
            description="Show Claude mobile app download links.",
            command_type="local_ui",
            aliases=["ios", "android"],
        ),
        usage="/mobile",
        handler=handler,
    )
