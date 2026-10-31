from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

PR_COMMENTS_PROMPT = """
You are an AI assistant integrated into a git-based version control system. Fetch and display comments from a GitHub pull request.

Steps:
1. Use `gh pr view --json number,headRepository` to get the PR number and repository info.
2. Use `gh api /repos/{{owner}}/{{repo}}/issues/{{number}}/comments` to get PR-level comments.
3. Use `gh api /repos/{{owner}}/{{repo}}/pulls/{{number}}/comments` to get review comments.
4. Format the comments clearly, including file and line references when available.
5. Return only the formatted comments.

If there are no comments, return "No comments found."

Additional user input: {args}
""".strip()


def build_pr_comments_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context
        return CommandResult(
            kind="prompt",
            prompt=PR_COMMENTS_PROMPT.format(args=invocation.args.strip() or "(none)"),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="pr-comments",
            description="Get comments from a GitHub pull request.",
            command_type="prompt",
        ),
        usage="/pr-comments [context]",
        handler=handler,
    )
