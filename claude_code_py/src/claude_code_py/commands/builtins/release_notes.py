import re

import httpx

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec

CHANGELOG_URL = "https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md"
RAW_CHANGELOG_URL = (
    "https://raw.githubusercontent.com/anthropics/claude-code/refs/heads/main/CHANGELOG.md"
)


def build_release_notes_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context, invocation
        notes = _fetch_release_notes()
        if notes is None:
            return CommandResult(
                kind="message",
                message=f"See the full changelog at: {CHANGELOG_URL}",
            )
        return CommandResult(kind="message", message=notes)

    return SlashCommand(
        spec=CommandSpec(
            name="release-notes",
            description="View release notes.",
            command_type="local_ui",
        ),
        usage="/release-notes",
        handler=handler,
    )


def _fetch_release_notes() -> str | None:
    try:
        response = httpx.get(RAW_CHANGELOG_URL, timeout=1.0, follow_redirects=True)
        response.raise_for_status()
    except Exception:
        return None

    sections = re.findall(
        r"^##\s+([^\n]+)\n(.*?)(?=^##\s+|\Z)",
        response.text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not sections:
        return None

    rendered: list[str] = []
    for version, body in sections[:3]:
        bullets = re.findall(r"^\s*[-*]\s+(.+)$", body, flags=re.MULTILINE)
        if not bullets:
            continue
        rendered.append(f"Version {version.strip()}:")
        rendered.extend(f"· {bullet.strip()}" for bullet in bullets[:8])
        rendered.append("")
    return "\n".join(rendered).strip() or None
