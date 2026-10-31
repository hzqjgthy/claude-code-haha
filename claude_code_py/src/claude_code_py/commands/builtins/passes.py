from claude_code_py.commands.builtins._helpers import try_open_url
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

PASSES_URL = "https://claude.ai/settings/referrals"


def build_passes_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        context.runtime_state_store.update_preferences(has_visited_passes=True)
        opened = try_open_url(PASSES_URL)
        return CommandResult(
            kind="message",
            message=(
                "Opening guest passes page in browser..."
                if opened
                else f"Visit {PASSES_URL} to manage guest passes."
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="passes",
            description="Share a free week of Claude Code with friends.",
            command_type="local_ui",
        ),
        usage="/passes",
        handler=handler,
    )
