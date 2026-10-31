from claude_code_py.commands.builtins._helpers import try_open_url
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

GITHUB_APP_URL = "https://github.com/apps/claude"


def build_install_github_app_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del invocation
        repo_hint = _detect_repo_hint(context)
        opened = try_open_url(GITHUB_APP_URL)
        message = (
            "Opening Claude GitHub app installation page..."
            if opened
            else f"Open this URL in your browser: {GITHUB_APP_URL}"
        )
        if repo_hint:
            message += f"\nDetected repository: {repo_hint}"
        return CommandResult(kind="message", message=message)

    return SlashCommand(
        spec=CommandSpec(
            name="install-github-app",
            description="Set up Claude GitHub Actions for a repository.",
            command_type="local_ui",
        ),
        usage="/install-github-app",
        handler=handler,
    )


def _detect_repo_hint(context: CommandContext) -> str | None:
    shell = context.tool_context.shell_provider
    if shell is None:
        return None
    try:
        result = shell.run(
            "git remote get-url origin",
            cwd=context.workspace_root,
            timeout=5,
        )
    except Exception:
        return None
    if result.exit_code != 0:
        return None
    return result.stdout.strip() or None
