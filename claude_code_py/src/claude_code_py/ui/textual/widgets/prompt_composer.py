from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Input, Static
from rich.text import Text

from claude_code_py.ui.state import PromptState, StatusDetailState, StatusSnapshot


class ComposerInput(Input):
    BINDINGS = [
        *Input.BINDINGS,
        Binding("up", "cycle_previous_suggestion", "Previous Suggestion", show=False, priority=True),
        Binding("down", "cycle_next_suggestion", "Next Suggestion", show=False, priority=True),
        Binding("tab", "apply_suggestion", "Apply Suggestion", show=False, priority=True),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.on_cycle_suggestion: Callable[[int], None] | None = None
        self.on_apply_suggestion: Callable[[], str] | None = None

    def action_cycle_previous_suggestion(self) -> None:
        if self.on_cycle_suggestion is not None:
            self.on_cycle_suggestion(-1)

    def action_cycle_next_suggestion(self) -> None:
        if self.on_cycle_suggestion is not None:
            self.on_cycle_suggestion(1)

    def action_apply_suggestion(self) -> None:
        if self.on_apply_suggestion is None:
            return
        next_text = self.on_apply_suggestion()
        self.value = next_text
        self.cursor_position = len(next_text)


class PromptComposer(Static):
    DEFAULT_CSS = """
    PromptComposer {
        height: auto;
        background: rgb(0,0,0);
        color: rgb(255,255,255);
    }

    #composer-notices {
        color: rgb(153,153,153);
        min-height: 1;
        margin: 0 0 1 0;
        min-height: 0;
    }

    #composer-frame {
        height: auto;
        border-top: solid rgb(136,136,136);
        padding: 0 0 0 0;
    }

    #composer-input-row {
        height: auto;
        align: left top;
    }

    #composer-prompt-char {
        width: 2;
        color: rgb(136,136,136);
        padding-top: 0;
        margin-right: 1;
    }

    #composer-input {
        border: none;
        background: transparent;
        color: rgb(255,255,255);
        padding: 0;
        margin: 0;
        width: 1fr;
    }

    #composer-hint-line {
        color: rgb(153,153,153);
        margin-top: 1;
        min-height: 0;
    }

    #composer-footer-row {
        margin-top: 1;
        height: auto;
    }

    #composer-footer-left {
        width: 1fr;
        color: rgb(153,153,153);
    }

    #composer-footer-right {
        width: auto;
        color: rgb(153,153,153);
        text-align: right;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._prompt_state = PromptState()
        self._footer_lines: list[str] = []
        self._status: StatusSnapshot | None = None
        self._detail: StatusDetailState | None = None
        self._runtime_message = "Idle"
        self._task_summary_lines: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static(id="composer-notices")
        with Horizontal(id="composer-frame"):
            with Horizontal(id="composer-input-row"):
                yield Static("❯", id="composer-prompt-char")
                yield ComposerInput(
                    placeholder='Try "explain this code" or type /help',
                    id="composer-input",
                )
        yield Static(id="composer-hint-line")
        with Horizontal(id="composer-footer-row"):
            yield Static(id="composer-footer-left")
            yield Static(id="composer-footer-right")

    def focus_input(self) -> None:
        self.query_one("#composer-input", ComposerInput).focus()

    def set_disabled(self, disabled: bool) -> None:
        self.query_one("#composer-input", ComposerInput).disabled = disabled

    def clear(self) -> None:
        self.query_one("#composer-input", ComposerInput).value = ""

    def set_suggestion_handlers(
        self,
        *,
        on_cycle: Callable[[int], None],
        on_apply: Callable[[], str],
    ) -> None:
        input_widget = self.query_one("#composer-input", ComposerInput)
        input_widget.on_cycle_suggestion = on_cycle
        input_widget.on_apply_suggestion = on_apply

    def update_prompt_state(self, prompt: PromptState) -> None:
        self._prompt_state = prompt
        self._render_prompt_indicator()
        self._render_notices()
        self._render_hint_line()
        self._render_footer()

    def update_footer(self, lines: list[str]) -> None:
        self._footer_lines = lines
        self._render_footer()

    def update_status(
        self,
        status: StatusSnapshot | None,
        detail: StatusDetailState | None,
        runtime_message: str,
        task_summary_lines: list[str],
    ) -> None:
        self._status = status
        self._detail = detail
        self._runtime_message = runtime_message
        self._task_summary_lines = task_summary_lines
        self._render_prompt_indicator()
        self._render_notices()
        self._render_hint_line()
        self._render_footer()

    def _render_notices(self) -> None:
        notices_widget = self.query_one("#composer-notices", Static)
        parts: list[str] = []
        if self._runtime_message != "Idle":
            parts.append(self._runtime_message.lower())
        if self._detail is not None and self._detail.pending_permission_count > 0:
            parts.append(
                f"{self._detail.pending_permission_count} approval pending"
            )
        if self._status is not None:
            remote = self._status.remote_status
            if remote.mode != "local":
                parts.append(
                    f"{remote.mode} {'connected' if remote.connected else 'offline'}"
                )
        notices_widget.update(
            Text(" · ".join(parts), style="rgb(153,153,153)") if parts else ""
        )

    def _render_hint_line(self) -> None:
        hint_widget = self.query_one("#composer-hint-line", Static)
        if self._prompt_state.suggestions:
            hint_widget.update("")
            return
        if self._runtime_message != "Idle":
            hint_widget.update("")
            return
        if self._detail is not None and self._detail.pending_permission_count > 0:
            hint_widget.update("")
            return
        if self._prompt_state.hints:
            hint_widget.update(
                Text(self._prompt_state.hints[0], style="rgb(153,153,153)")
            )
            return
        hint_widget.update("")

    def _render_prompt_indicator(self) -> None:
        prompt_char = self.query_one("#composer-prompt-char", Static)
        if self._runtime_message != "Idle":
            prompt_char.update(Text("❯", style="rgb(153,153,153)"))
            return
        if self._prompt_state.mode == "command":
            prompt_char.update(Text("❯", style="rgb(177,185,249)"))
            return
        prompt_char.update(Text("❯", style="rgb(136,136,136)"))

    def _render_footer(self) -> None:
        left = self.query_one("#composer-footer-left", Static)
        right = self.query_one("#composer-footer-right", Static)
        left_render = Text()
        left_items = []
        left_items.append(
            "command mode" if self._prompt_state.mode == "command" else "prompt mode"
        )
        left_items.append(
            f"{self._status.permission_mode} permissions"
            if self._status is not None
            else "default permissions"
        )
        left_items.append("Ctrl+O transcript")
        left_items.append("F6 copy")
        left_render.append(" · ".join(left_items), style="rgb(153,153,153)")
        shortcut_line = (
            self._footer_lines[1]
            if len(self._footer_lines) > 1
            else "/help /status /memory /sessions /share /rewind"
        )
        if shortcut_line:
            left_render.append("\n")
            left_render.append(
                f"F1 help · {shortcut_line}",
                style="rgb(153,153,153)",
            )
        left.update(left_render)

        right_render = Text()
        right_items: list[str] = []
        if self._detail is not None:
            right_items.append(f"tasks {self._detail.task_count}")
            right_items.append(f"entries {self._detail.transcript_entries}")
        if self._status is not None:
            right_items.append(f"model {self._status.model}")
        if right_items:
            right_render.append(" · ".join(right_items), style="rgb(153,153,153)")
        if self._task_summary_lines and self._task_summary_lines[0] != "No tasks":
            if right_render.plain:
                right_render.append("\n")
            right_render.append(self._task_summary_lines[0], style="rgb(153,153,153)")
        right.update(right_render)

    def input_widget(self) -> ComposerInput:
        return self.query_one("#composer-input", ComposerInput)
