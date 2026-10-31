from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

INIT_PROMPT = """
Please analyze this codebase and create a CLAUDE.md file that will be given to future Claude Code sessions in this repository.

What to add:
1. Commands commonly used to build, lint, and test this codebase, including how to run a single test if relevant.
2. High-level code architecture and structure so future Claude sessions can become productive quickly.

Usage notes:
- If CLAUDE.md already exists, suggest concrete improvements instead of rewriting blindly.
- Keep it concise and avoid generic engineering advice.
- Include important guidance from README, Copilot/Cursor rules, AGENTS.md, and related AI-tooling files if present.
- Do not make up commands or workflows that you cannot verify from the repository.

Prefix the file with:

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
""".strip()


def build_init_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context
        extra = invocation.args.strip()
        prompt = INIT_PROMPT
        if extra:
            prompt = f"{prompt}\n\nAdditional user note:\n{extra}"
        return CommandResult(kind="prompt", prompt=prompt)

    return SlashCommand(
        spec=CommandSpec(
            name="init",
            description="Initialize a new CLAUDE.md file with codebase documentation.",
            command_type="prompt",
        ),
        usage="/init",
        handler=handler,
    )
