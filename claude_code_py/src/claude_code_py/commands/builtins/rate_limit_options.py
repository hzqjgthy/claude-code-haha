from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_rate_limit_options_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context, invocation
        lines = [
            "Rate limit options:",
            "- /upgrade",
            "- /extra-usage on",
            "- wait for limits to reset",
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            selector_kind="selector:rate-limit-options",
            selector_title="Rate Limit Options",
            selector_options=[
                CommandSelectorOption(
                    label="Upgrade your plan",
                    command="/upgrade",
                    description="Open the Max upgrade flow.",
                ),
                CommandSelectorOption(
                    label="Enable extra usage",
                    command="/extra-usage on",
                    description="Open billing and mark extra usage enabled.",
                ),
            ],
        )

    return SlashCommand(
        spec=CommandSpec(
            name="rate-limit-options",
            description="Show options when a rate limit is reached.",
            command_type="local_ui",
        ),
        usage="/rate-limit-options",
        handler=handler,
        hidden=True,
    )
