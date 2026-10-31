from claude_code_py.commands.builtins._helpers import try_open_url
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

SLACK_APP_URL = "https://slack.com/marketplace/A08SF47R6P4-claude"


def build_install_slack_app_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context, invocation
        opened = try_open_url(SLACK_APP_URL)
        return CommandResult(
            kind="message",
            message=(
                "Opening Slack app installation page in browser..."
                if opened
                else f"Couldn't open browser. Visit: {SLACK_APP_URL}"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="install-slack-app",
            description="Install the Claude Slack app.",
            command_type="local_ui",
        ),
        usage="/install-slack-app",
        handler=handler,
    )
