from __future__ import annotations

import re
from pathlib import Path

_ENV_LINE_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")


def update_env_file(path: Path, updates: dict[str, str | None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(updates)
    rendered: list[str] = []

    for line in lines:
        match = _ENV_LINE_PATTERN.match(line)
        if match is None:
            rendered.append(line)
            continue

        key = match.group(1)
        if key not in remaining:
            rendered.append(line)
            continue

        value = remaining.pop(key)
        if value is not None:
            rendered.append(f"{key}={_format_env_value(value)}")

    for key, value in remaining.items():
        if value is None:
            continue
        rendered.append(f"{key}={_format_env_value(value)}")

    normalized = "\n".join(rendered).rstrip()
    path.write_text(f"{normalized}\n" if normalized else "", encoding="utf-8")


def _format_env_value(value: str) -> str:
    if value == "":
        return '""'
    if any(char.isspace() for char in value) or "#" in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value
