from __future__ import annotations

import platform
import shutil
import subprocess
from collections.abc import Callable


class ClipboardError(RuntimeError):
    """Raised when no clipboard backend can accept copied text."""


def copy_text_to_clipboard(
    text: str,
    *,
    osc52_fallback: Callable[[str], None] | None = None,
) -> str:
    """Copy text to the system clipboard and return the backend name used."""

    for backend_name, command in _clipboard_commands():
        executable = command[0]
        if shutil.which(executable) is None:
            continue
        try:
            subprocess.run(
                command,
                input=text,
                text=True,
                check=True,
                capture_output=True,
            )
            return backend_name
        except (OSError, subprocess.SubprocessError):
            continue

    if osc52_fallback is not None:
        osc52_fallback(text)
        return "osc52"

    raise ClipboardError("No clipboard backend is available.")


def _clipboard_commands() -> list[tuple[str, list[str]]]:
    system = platform.system()
    if system == "Darwin":
        return [("pbcopy", ["pbcopy"])]
    if system == "Windows":
        return [("clip", ["clip"])]
    return [
        ("wl-copy", ["wl-copy"]),
        ("xclip", ["xclip", "-selection", "clipboard"]),
    ]
