from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from claude_code_py.ui.state import PromptState


class PromptOverlayWidget(Static):
    DEFAULT_CSS = """
    PromptOverlayWidget {
        display: none;
        height: auto;
        background: rgb(0,0,0);
        padding: 0 1 1 2;
    }

    #prompt-overlay-suggestions {
        width: 1fr;
        color: rgb(255,255,255);
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="prompt-overlay-suggestions")

    def update_state(
        self,
        *,
        prompt: PromptState,
    ) -> None:
        suggestions = render_prompt_overlay_suggestions(prompt)
        self.query_one("#prompt-overlay-suggestions", Static).update(suggestions)
        has_content = bool(isinstance(suggestions, Text) and suggestions.plain)
        self.display = has_content


def render_prompt_overlay_suggestions(prompt: PromptState) -> Text:
    rendered = Text()
    if not prompt.suggestions:
        return rendered
    start, end = _suggestion_window(
        len(prompt.suggestions),
        prompt.selected_suggestion,
        max_items=5,
    )
    if start > 0:
        rendered.append("  ...\n", style="dim")
    for visible_index, item in enumerate(prompt.suggestions[start:end], start=start):
        index = visible_index
        if index > 0:
            rendered.append("\n")
        selected = index == prompt.selected_suggestion
        prefix = "❯ " if selected else "  "
        rendered.append(
            prefix,
            style="bold rgb(177,185,249)" if selected else "rgb(153,153,153)",
        )
        rendered.append(
            item.value,
            style="bold rgb(177,185,249)" if selected else "bold white",
        )
        if item.description:
            rendered.append("  ")
            rendered.append(
                item.description,
                style="rgb(177,185,249)" if selected else "rgb(153,153,153)",
            )
    if end < len(prompt.suggestions):
        rendered.append("\n")
        rendered.append("  ...", style="dim")
    return rendered


def _suggestion_window(
    total: int,
    selected: int,
    *,
    max_items: int,
) -> tuple[int, int]:
    if total <= max_items:
        return 0, total
    half = max_items // 2
    start = max(0, selected - half)
    end = start + max_items
    if end > total:
        end = total
        start = end - max_items
    return start, end
