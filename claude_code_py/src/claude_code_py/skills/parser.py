from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(slots=True)
class SkillDefinition:
    name: str
    command_name: str
    description: str
    content: str
    when_to_use: str | None
    user_invocable: bool
    argument_hint: str | None
    source_path: Path
    source_scope: str


FRONTMATTER_PATTERN = re.compile(r"^---\n(?P<frontmatter>.*?)\n---\n?", re.DOTALL)


def parse_skill_markdown(
    content: str,
    *,
    source_path: Path,
    source_scope: str,
) -> SkillDefinition:
    frontmatter, body = parse_frontmatter(content)
    stem = source_path.parent.name if source_path.name == "SKILL.md" else source_path.stem
    command_name = slugify(
        str(frontmatter.get("command") or frontmatter.get("name") or stem),
    )
    name = str(frontmatter.get("name") or stem)
    description = str(frontmatter.get("description") or "").strip()
    when_to_use = _optional_string(
        frontmatter.get("when_to_use") or frontmatter.get("when-to-use"),
    )
    argument_hint = _optional_string(
        frontmatter.get("argument_hint") or frontmatter.get("argument-hint"),
    )
    user_invocable = _parse_bool(
        frontmatter.get("user_invocable") or frontmatter.get("user-invocable"),
        default=False,
    )
    return SkillDefinition(
        name=name,
        command_name=command_name,
        description=description,
        content=body.strip(),
        when_to_use=when_to_use,
        user_invocable=user_invocable,
        argument_hint=argument_hint,
        source_path=source_path,
        source_scope=source_scope,
    )


def parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    match = FRONTMATTER_PATTERN.match(content)
    if match is None:
        return {}, content
    frontmatter_text = match.group("frontmatter")
    body = content[match.end() :]
    return parse_frontmatter_mapping(frontmatter_text), body


def parse_frontmatter_mapping(raw_text: str) -> dict[str, object]:
    result: dict[str, object] = {}
    current_key: str | None = None

    for raw_line in raw_text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("- ") and current_key is not None:
            existing = result.setdefault(current_key, [])
            if not isinstance(existing, list):
                existing = [existing]
                result[current_key] = existing
            existing.append(_coerce_scalar(line[2:].strip()))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip()
        stripped_value = value.strip()
        current_key = normalized_key
        if stripped_value == "":
            result[normalized_key] = []
            continue
        result[normalized_key] = _coerce_scalar(stripped_value)
    return result


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "skill"


def _coerce_scalar(value: str) -> object:
    stripped = value.strip().strip("'\"")
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return stripped


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _parse_bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
