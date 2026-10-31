from __future__ import annotations

from difflib import unified_diff
from pathlib import Path


def relativize_path(path: Path, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def safe_read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def build_unified_diff(
    before: str,
    after: str,
    *,
    fromfile: str,
    tofile: str,
    max_lines: int = 80,
) -> str:
    lines = list(
        unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
        )
    )
    if len(lines) <= max_lines:
        return "\n".join(lines).strip()
    clipped = lines[:max_lines]
    clipped.append(f"... truncated {len(lines) - max_lines} more line(s)")
    return "\n".join(clipped).strip()


def clip_text(
    text: str,
    *,
    max_lines: int = 40,
    max_chars: int = 4000,
) -> str:
    sliced = text[:max_chars]
    lines = sliced.splitlines()
    if len(lines) <= max_lines and len(sliced) == len(text):
        return sliced.strip()
    clipped = lines[:max_lines]
    suffix = "..." if len(sliced) < len(text) or len(lines) > max_lines else ""
    return "\n".join(clipped).strip() + suffix
