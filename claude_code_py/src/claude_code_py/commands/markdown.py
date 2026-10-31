from dataclasses import dataclass
from pathlib import Path
import re

from claude_code_py.skills.parser import parse_frontmatter


@dataclass(slots=True)
class MarkdownCommandDefinition:
    name: str
    command_name: str
    description: str
    content: str
    argument_hint: str | None
    when_to_use: str | None
    source_path: Path
    source_scope: str


def parse_markdown_command(
    content: str,
    *,
    source_path: Path,
    source_scope: str,
) -> MarkdownCommandDefinition:
    frontmatter, body = parse_frontmatter(content)
    stem = source_path.parent.name if source_path.name == "SKILL.md" else source_path.stem
    command_name = slugify(
        str(frontmatter.get("command") or frontmatter.get("name") or stem),
    )
    name = str(frontmatter.get("name") or stem)
    description = str(frontmatter.get("description") or "").strip()
    argument_hint = optional_string(
        frontmatter.get("argument_hint") or frontmatter.get("argument-hint"),
    )
    when_to_use = optional_string(
        frontmatter.get("when_to_use") or frontmatter.get("when-to-use"),
    )
    return MarkdownCommandDefinition(
        name=name,
        command_name=command_name,
        description=description,
        content=body.strip(),
        argument_hint=argument_hint,
        when_to_use=when_to_use,
        source_path=source_path,
        source_scope=source_scope,
    )


def iter_markdown_command_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix.lower() == ".md" or root.name == "SKILL.md" else []
    if not root.exists():
        return []
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".md" or path.name == "SKILL.md":
            files.append(path)
    return files


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "command"


def optional_string(value: object) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None
