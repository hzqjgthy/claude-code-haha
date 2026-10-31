from rich.text import Text

from claude_code_py.ui.state import TranscriptEntry


def render_transcript_entry(entry: TranscriptEntry) -> Text:
    if entry.text.startswith("Tool call:"):
        return _render_special("tool", entry.text, color="rgb(177,185,249)")
    if entry.text.startswith("Tool result:"):
        color = "rgb(255,107,128)" if entry.kind == "error" else "rgb(122,180,232)"
        label = "tool-error" if entry.kind == "error" else "tool-result"
        return _render_special(label, entry.text, color=color)
    if entry.text.startswith("Permission requested:"):
        return _render_special("permission", entry.text, color="rgb(177,185,249)")
    if entry.text.startswith("Saved file:"):
        return _render_special("edited", entry.text, color="rgb(122,180,232)")
    if entry.text.startswith("Conversation exported to:"):
        return _render_special("export", entry.text, color="rgb(78,186,101)")
    if entry.text.startswith("Share bundle written to:"):
        return _render_special("share", entry.text, color="rgb(78,186,101)")
    if entry.text.startswith("Initialized memory file at"):
        return _render_special("memory", entry.text, color="rgb(78,186,101)")
    if entry.text.startswith("Rewound session"):
        return _render_special("rewind", entry.text, color="rgb(175,135,255)")
    if entry.text.startswith("Resumed session") or entry.text.startswith("Forked from session"):
        return _render_special("session", entry.text, color="rgb(122,180,232)")
    if entry.text.startswith("Plugins and skills reloaded."):
        return _render_special("reload", entry.text, color="rgb(78,186,101)")
    if "warning:" in entry.text.lower():
        return _render_special("warning", entry.text, color="rgb(255,193,7)")

    rendered = Text()
    if entry.kind == "user":
        rendered.append("❯ ", style="rgb(80,80,80) on rgb(55,55,55)")
        rendered.append(entry.text, style="rgb(255,255,255) on rgb(55,55,55)")
        rendered.append(" ", style="on rgb(55,55,55)")
        return rendered
    if entry.kind == "assistant":
        rendered.append(entry.text, style="white")
        return rendered
    if entry.kind == "error":
        rendered.append("! ", style="bold rgb(255,107,128)")
        rendered.append(entry.text, style="rgb(255,107,128)")
        return rendered
    rendered.append(entry.text, style="rgb(153,153,153)")
    return rendered


def _render_special(label: str, text: str, *, color: str) -> Text:
    rendered = Text()
    rendered.append(f"{label}: ", style=f"bold {color}")
    rendered.append(text, style="rgb(255,255,255)")
    return rendered
