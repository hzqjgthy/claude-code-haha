from __future__ import annotations

import webbrowser

THEME_OPTIONS = (
    "auto",
    "dark",
    "light",
    "light-daltonized",
    "dark-daltonized",
    "light-ansi",
    "dark-ansi",
)

OUTPUT_STYLE_OPTIONS = (
    "default",
    "Explanatory",
    "Learning",
)


def format_duration_ms(duration_ms: int) -> str:
    total_seconds = max(duration_ms, 0) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def bool_word(value: bool) -> str:
    return "on" if value else "off"


def try_open_url(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False
