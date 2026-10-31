from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

SECURITY_REVIEW_PROMPT = """
You are a senior security engineer conducting a focused security review of the pending changes on this branch.

Review objective:
- Identify high-confidence security vulnerabilities introduced by the current branch.
- Focus on concrete exploitability, not generic best practices.
- Prefer high and medium findings only.

Use repository tools to inspect:
- `git status`
- `git diff --name-only origin/HEAD...`
- `git log --no-decorate origin/HEAD...`
- `git diff origin/HEAD...`

Required output:
- Markdown only
- File and line reference
- Severity
- Vulnerability category
- Description
- Exploit scenario
- Fix recommendation

Ignore speculative issues and obvious false positives.
""".strip()


def build_security_review_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context
        extra = invocation.args.strip()
        prompt = SECURITY_REVIEW_PROMPT
        if extra:
            prompt = f"{prompt}\n\nAdditional user input:\n{extra}"
        return CommandResult(kind="prompt", prompt=prompt)

    return SlashCommand(
        spec=CommandSpec(
            name="security-review",
            description="Complete a security review of the pending changes on the current branch.",
            command_type="prompt",
        ),
        usage="/security-review",
        handler=handler,
    )
