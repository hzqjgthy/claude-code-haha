from __future__ import annotations

import io
from importlib.metadata import PackageNotFoundError, version

from rich.console import Console
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalGroup, VerticalScroll
from textual.widgets import Input, Static

from claude_code_py.ui.state import (
    PermissionRequestState,
    StatusDetailState,
    StatusSnapshot,
    TranscriptEntry,
)
from claude_code_py.ui.textual.messages import render_transcript_entry


class _TranscriptEntryWidget(Static):
    DEFAULT_CSS = """
    _TranscriptEntryWidget {
        width: 1fr;
        height: auto;
        background: transparent;
        color: rgb(255,255,255);
        padding: 0;
        margin: 0;
    }
    """

    def __init__(self, entry: TranscriptEntry, *, entry_index: int) -> None:
        super().__init__()
        self.entry = entry
        self.entry_index = entry_index
        self._matched = False
        self._current = False
        self.update_render()

    def update_search_state(self, *, matched: bool, current: bool) -> None:
        if matched == self._matched and current == self._current:
            return
        self._matched = matched
        self._current = current
        self.update_render()

    def update_render(self) -> None:
        rendered = TranscriptWidget.render_entry(
            self.entry,
            matched=self._matched,
            current=self._current,
        )
        self.update(rendered)


class TranscriptWidget(VerticalScroll, can_focus=True):
    DEFAULT_CSS = """
    TranscriptWidget {
        background: rgb(0,0,0);
        color: rgb(255,255,255);
        padding: 0;
        margin: 0;
        border: none;
        overflow-x: hidden;
        overflow-y: auto;
    }

    #transcript-search-bar {
        display: none;
        dock: top;
        height: auto;
        margin: 0 1 1 1;
        border-bottom: solid rgb(80,80,80);
        padding-bottom: 1;
        background: rgb(0,0,0);
    }

    #transcript-search-input {
        width: 1fr;
        border: none;
        background: transparent;
        color: rgb(255,255,255);
    }

    #transcript-search-status {
        width: 10;
        text-align: right;
        color: rgb(153,153,153);
        padding-left: 1;
    }

    #transcript-content {
        width: 1fr;
        height: auto;
        layout: vertical;
        background: rgb(0,0,0);
        padding: 0 1;
    }

    #transcript-spacer {
        display: none;
        width: 1fr;
        height: auto;
        background: rgb(0,0,0);
    }

    #transcript-intro {
        display: none;
        width: 1fr;
        height: auto;
        margin-bottom: 1;
        color: rgb(255,255,255);
        background: rgb(0,0,0);
    }

    #transcript-stack {
        width: 1fr;
        height: auto;
        layout: vertical;
        background: rgb(0,0,0);
    }
    """

    def __init__(
        self,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._entries: list[TranscriptEntry] = []
        self._entry_widgets: list[_TranscriptEntryWidget] = []
        self._search_query = ""
        self._search_matches: list[int] = []
        self._current_match = -1
        self._unseen_count = 0
        self._status: StatusSnapshot | None = None
        self._detail: StatusDetailState | None = None
        self._runtime_message = "Idle"
        self._permission_request: PermissionRequestState | None = None
        self._task_summary_lines: list[str] = []
        self._intro_rendered = Text()

    def compose(self) -> ComposeResult:
        with Horizontal(id="transcript-search-bar"):
            yield Input(placeholder="Search transcript", id="transcript-search-input")
            yield Static("", id="transcript-search-status")
        with VerticalGroup(id="transcript-content"):
            yield Static("", id="transcript-spacer")
            yield Static("", id="transcript-intro")
            yield VerticalGroup(id="transcript-stack")

    def on_mount(self) -> None:
        self._schedule_bottom_anchor_sync()

    def on_resize(self, _event=None) -> None:
        self._schedule_bottom_anchor_sync()

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        self.on_log_scrolled()

    def log_widget(self) -> TranscriptWidget:
        return self

    def search_input_widget(self) -> Input:
        return self.query_one("#transcript-search-input", Input)

    def focus_log(self) -> None:
        self.focus()

    def open_search(self) -> None:
        search_bar = self.query_one("#transcript-search-bar", Horizontal)
        search_bar.display = True
        search_input = self.search_input_widget()
        search_input.value = self._search_query
        search_input.focus()
        self._render_search_status()
        self._schedule_bottom_anchor_sync()

    def close_search(
        self,
        *,
        clear_query: bool = False,
        refocus_log: bool = False,
    ) -> None:
        self.query_one("#transcript-search-bar", Horizontal).display = False
        if clear_query:
            self._search_query = ""
            self._search_matches = []
            self._current_match = -1
            self._refresh_search_highlights()
        if refocus_log:
            self.focus_log()
        self._schedule_bottom_anchor_sync()

    def is_search_open(self) -> bool:
        return self.query_one("#transcript-search-bar", Horizontal).display

    def update_context(
        self,
        *,
        status: StatusSnapshot | None,
        detail: StatusDetailState | None,
        runtime_message: str,
        permission_request: PermissionRequestState | None,
        task_summary_lines: list[str],
    ) -> None:
        self._status = status
        self._detail = detail
        self._runtime_message = runtime_message
        self._permission_request = permission_request
        self._task_summary_lines = task_summary_lines
        self._render_intro()
        self._schedule_bottom_anchor_sync()

    def append_entries(self, entries: list[TranscriptEntry]) -> None:
        if not entries:
            return
        was_at_bottom = self.is_vertical_scroll_end
        base_index = len(self._entries)
        self._entries.extend(entries)
        new_widgets = [
            _TranscriptEntryWidget(entry, entry_index=base_index + offset)
            for offset, entry in enumerate(entries)
        ]
        self._entry_widgets.extend(new_widgets)
        self._stack_widget().mount(*new_widgets)
        if self._search_query:
            self._refresh_search_matches(preserve_current=True)
            self._refresh_search_highlights()
        if not was_at_bottom:
            self._unseen_count += sum(1 for entry in entries if entry.kind != "user")
        else:
            self._unseen_count = 0
            self._schedule_scroll_end()
        self._render_intro()
        self._schedule_bottom_anchor_sync()

    def replace_entries(self, entries: list[TranscriptEntry]) -> None:
        self._entries = list(entries)
        self._entry_widgets = []
        stack = self._stack_widget()
        stack.remove_children()
        widgets = [
            _TranscriptEntryWidget(entry, entry_index=index)
            for index, entry in enumerate(entries)
        ]
        self._entry_widgets.extend(widgets)
        stack.mount(*widgets)
        self._unseen_count = 0
        self._refresh_search_matches(preserve_current=False)
        self._refresh_search_highlights()
        self._render_intro()
        self._schedule_bottom_anchor_sync(scroll_to_end=True)

    def export_plain_text(self) -> str:
        return render_transcript_plain_text(self._entries)

    def next_search_match(self) -> None:
        if not self._search_matches:
            return
        self._current_match = (self._current_match + 1) % len(self._search_matches)
        self._refresh_search_highlights()
        self._jump_to_current_match()

    def previous_search_match(self) -> None:
        if not self._search_matches:
            return
        self._current_match = (self._current_match - 1) % len(self._search_matches)
        self._refresh_search_highlights()
        self._jump_to_current_match()

    def on_log_scrolled(self) -> None:
        if self.is_vertical_scroll_end:
            self._unseen_count = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "transcript-search-input":
            return
        self._search_query = event.value
        self._refresh_search_matches(preserve_current=False)
        self._refresh_search_highlights()
        if self._search_matches:
            self._jump_to_current_match()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "transcript-search-input":
            return
        self.close_search(clear_query=False, refocus_log=True)
        self._jump_to_current_match()

    @staticmethod
    def render_entry(
        entry: TranscriptEntry,
        *,
        matched: bool = False,
        current: bool = False,
    ) -> Text:
        rendered = render_transcript_entry(entry)
        if matched:
            rendered = rendered.copy()
            style = "on rgb(31,48,74)" if not current else "bold on rgb(62,94,145)"
            rendered.stylize(style)
        return rendered

    def _stack_widget(self) -> VerticalGroup:
        return self.query_one("#transcript-stack", VerticalGroup)

    def _intro_widget(self) -> Static:
        return self.query_one("#transcript-intro", Static)

    def _spacer_widget(self) -> Static:
        return self.query_one("#transcript-spacer", Static)

    def _render_intro(self) -> None:
        intro = self._intro_widget()
        if any(entry.kind in {"user", "assistant"} for entry in self._entries):
            intro.display = False
            intro.update("")
            self._intro_rendered = Text()
            return
        rendered = render_transcript_intro(
            status=self._status,
            detail=self._detail,
            runtime_message=self._runtime_message,
            permission_request=self._permission_request,
            task_summary_lines=self._task_summary_lines,
        )
        intro.update(rendered)
        intro.display = bool(rendered.plain)
        self._intro_rendered = rendered if intro.display else Text()

    def _refresh_search_matches(self, *, preserve_current: bool) -> None:
        self._search_matches = find_search_matches(self._entries, self._search_query)
        if not self._search_matches:
            self._current_match = -1
            self._render_search_status()
            return
        if preserve_current and self._current_match >= 0:
            self._current_match = min(self._current_match, len(self._search_matches) - 1)
        else:
            self._current_match = 0
        self._render_search_status()

    def _refresh_search_highlights(self) -> None:
        for index, widget in enumerate(self._entry_widgets):
            widget.update_search_state(
                matched=index in self._search_matches,
                current=self._is_current_match(index),
            )
        self._render_search_status()

    def _jump_to_current_match(self) -> None:
        if not self._search_matches or self._current_match < 0:
            return
        target_index = self._search_matches[self._current_match]
        if not (0 <= target_index < len(self._entry_widgets)):
            return
        self.scroll_to_widget(
            self._entry_widgets[target_index],
            animate=False,
            center=True,
            immediate=True,
        )

    def _render_search_status(self) -> None:
        status = self.query_one("#transcript-search-status", Static)
        if not self._search_query:
            status.update("")
            return
        if not self._search_matches:
            status.update("0/0")
            return
        status.update(f"{self._current_match + 1}/{len(self._search_matches)}")

    def _is_current_match(self, index: int) -> bool:
        if self._current_match < 0 or not self._search_matches:
            return False
        return self._search_matches[self._current_match] == index

    def _schedule_bottom_anchor_sync(self, *, scroll_to_end: bool = False) -> None:
        def refresh_layout() -> None:
            self._sync_bottom_anchor()
            if scroll_to_end:
                self.scroll_end(animate=False, immediate=True, x_axis=False)

        self.call_after_refresh(refresh_layout)

    def _schedule_scroll_end(self) -> None:
        self.call_after_refresh(
            lambda: self.scroll_end(animate=False, immediate=True, x_axis=False)
        )

    def _sync_bottom_anchor(self) -> None:
        spacer = self._spacer_widget()
        padding_lines = compute_bottom_padding_lines(
            content_lines=self._estimate_content_lines(),
            viewport_height=self._content_viewport_height(),
        )
        if padding_lines <= 0:
            spacer.display = False
            spacer.update("")
            return
        spacer.display = True
        spacer.update(render_blank_lines(padding_lines))

    def _estimate_content_lines(self) -> int:
        width = self._content_width()
        if width <= 0:
            return 0
        line_count = 0
        if self._intro_rendered.plain:
            line_count += count_rendered_lines(self._intro_rendered, width=width)
            line_count += 1
        for entry in self._entries:
            line_count += count_rendered_lines(self.render_entry(entry), width=width)
        return line_count

    def _content_viewport_height(self) -> int:
        search_bar_height = 0
        search_bar = self.query_one("#transcript-search-bar", Horizontal)
        if search_bar.display:
            search_bar_height = search_bar.region.height or search_bar.size.height
        return max(0, self.size.height - search_bar_height)

    def _content_width(self) -> int:
        content = self.query_one("#transcript-content", VerticalGroup)
        width = content.region.width or content.size.width or self.size.width
        return max(0, width - 2)


def render_transcript_intro(
    *,
    status: StatusSnapshot | None,
    detail: StatusDetailState | None,
    runtime_message: str,
    permission_request: PermissionRequestState | None,
    task_summary_lines: list[str],
) -> Text:
    rendered = Text()
    rendered.append("Claude Code", style="bold rgb(215,119,87)")
    rendered.append(f" v{_package_version()}", style="rgb(153,153,153)")
    if detail is not None and detail.project_name:
        rendered.append("\n")
        rendered.append(detail.project_name, style="rgb(255,255,255)")
        if detail.cwd_name:
            rendered.append(" · ", style="rgb(80,80,80)")
            rendered.append(detail.cwd_name, style="rgb(153,153,153)")
    meta_bits: list[str] = []
    if status is not None:
        meta_bits.extend(
            [
                f"model {status.model}",
                f"{status.permission_mode} permissions",
                _remote_label(status),
            ]
        )
    if meta_bits:
        rendered.append("\n")
        rendered.append(" · ".join(meta_bits), style="rgb(153,153,153)")
    notice_bits: list[str] = []
    if runtime_message != "Idle":
        notice_bits.append(runtime_message.lower())
    if permission_request is not None:
        notice_bits.append("approval pending")
    if detail is not None and detail.task_count > 0:
        notice_bits.append(f"tasks {detail.task_count}")
    if task_summary_lines and task_summary_lines[0] != "No tasks":
        notice_bits.append(task_summary_lines[0])
    if notice_bits:
        rendered.append("\n")
        rendered.append(" · ".join(notice_bits), style="rgb(153,153,153)")
    rendered.append("\n")
    rendered.append(
        'Try "explain this code" or type /help',
        style="rgb(153,153,153)",
    )
    return rendered


def find_search_matches(entries: list[TranscriptEntry], query: str) -> list[int]:
    normalized = query.strip().lower()
    if not normalized:
        return []
    return [
        index
        for index, entry in enumerate(entries)
        if normalized in entry.text.lower()
    ]
def compute_bottom_padding_lines(
    *,
    content_lines: int,
    viewport_height: int,
) -> int:
    if content_lines <= 0 or viewport_height <= 0:
        return 0
    return max(0, viewport_height - content_lines)


def render_blank_lines(count: int) -> str:
    return "\n".join(" " for _ in range(count))


def count_rendered_lines(renderable: Text, *, width: int) -> int:
    if width <= 0:
        return 0
    console = Console(
        file=io.StringIO(),
        width=width,
        color_system=None,
        force_terminal=False,
        legacy_windows=False,
    )
    lines = console.render_lines(
        renderable,
        options=console.options.update(width=width),
        pad=False,
    )
    return max(1, len(lines))


def render_transcript_plain_text(entries: list[TranscriptEntry]) -> str:
    blocks = [_render_transcript_entry_plain_text(entry) for entry in entries]
    return "\n\n".join(block for block in blocks if block.strip())


def _render_transcript_entry_plain_text(entry: TranscriptEntry) -> str:
    if entry.kind == "user":
        lines = entry.text.splitlines() or [""]
        return "\n".join(f"> {line}" if line else ">" for line in lines)
    return render_transcript_entry(entry).plain


def _remote_label(status: StatusSnapshot) -> str:
    remote = status.remote_status
    if remote.mode == "local":
        return "local"
    if remote.connected:
        return f"{remote.mode} connected"
    return f"{remote.mode} offline"


def _package_version() -> str:
    try:
        return version("claude-code-py")
    except PackageNotFoundError:
        return "dev"
