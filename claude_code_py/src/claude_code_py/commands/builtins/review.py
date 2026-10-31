from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

LOCAL_REVIEW_PROMPT = """
You are an expert code reviewer. Follow these steps:

1. If no PR number is provided in the args, run `gh pr list` to show open PRs.
2. If a PR number is provided, run `gh pr view <number>` to get PR details.
3. Run `gh pr diff <number>` to get the diff.
4. Analyze the changes and provide a concise but thorough review that covers:
   - what the PR does
   - code quality and style concerns
   - specific improvement suggestions
   - risks or regressions

Focus on correctness, conventions, performance implications, test coverage, and security considerations.

PR number or extra context: {args}
""".strip()


def build_review_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context
        args = invocation.args.strip()
        prompt = LOCAL_REVIEW_PROMPT.format(args=args or "(none provided)")
        if args:
            prompt = f"{prompt}\n\nAdditional context:\n{args}"
        return CommandResult(
            kind="prompt",
            prompt=prompt,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="review",
            description="Review a pull request.",
            command_type="prompt",
            argument_hint="[pr number or context]",
        ),
        usage="/review [pr number or context]",
        handler=handler,
    )
