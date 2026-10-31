from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

ULTRAREVIEW_PROMPT = """
Run a deep bug-finding review of the current branch.

Goals:
- Find concrete, user-impacting bugs or regressions.
- Verify each finding against the changed code.
- Prioritize correctness, behavior changes, missing tests, and risk.

Return findings first, ordered by severity, with file and line references where possible.
""".strip()


def build_ultrareview_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context
        extra = invocation.args.strip()
        prompt = ULTRAREVIEW_PROMPT
        if extra:
            prompt = f"{prompt}\n\nAdditional context:\n{extra}"
        return CommandResult(kind="prompt", prompt=prompt)

    return SlashCommand(
        spec=CommandSpec(
            name="ultrareview",
            description="Find and verify bugs in your branch.",
            command_type="prompt",
        ),
        usage="/ultrareview [context]",
        handler=handler,
    )
