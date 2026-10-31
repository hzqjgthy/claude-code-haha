from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, OptionList, Static, TextArea
from textual.widgets.option_list import Option

from claude_code_py.domain.permissions import PermissionPromptChoice
from claude_code_py.ui.state import (
    EditorDialogState,
    InfoDialogActionState,
    PermissionRequestState,
    SelectorDialogState,
)


class InfoDialogPane(Static):
    DEFAULT_CSS = """
    InfoDialogPane {
        border-top: solid $primary;
        background: $boost;
        padding: 1 2 0 2;
        height: auto;
    }

    #info-scroll {
        max-height: 18;
        min-height: 8;
        border: none;
        padding: 0 1 0 0;
    }

    #info-command-actions {
        margin-top: 1;
    }

    #info-actions {
        margin-top: 1;
    }

    .info-action {
        margin-top: 1;
    }
    """

    def __init__(
        self,
        title: str,
        lines: list[str],
        *,
        on_close: Callable[[], None] | None = None,
        actions: list[InfoDialogActionState] | None = None,
        on_action: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self._title = title
        self._lines = lines
        self._on_close = on_close
        self._actions = actions or []
        self._on_action = on_action

    def compose(self) -> ComposeResult:
        content = "\n".join([self._title, "", *self._lines])
        with VerticalScroll(id="info-scroll"):
            yield Static(content)
        if self._actions:
            with Vertical(id="info-command-actions"):
                for index, action in enumerate(self._actions):
                    description = (
                        f" - {action.description}" if action.description else ""
                    )
                    yield Button(
                        f"{action.label}{description}",
                        id=f"info_action_{index}",
                        classes="info-action",
                        variant="default",
                    )
        with Horizontal(id="info-actions"):
            yield Button("Close", id="close_info", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_info" and self._on_close is not None:
            self._on_close()
            return
        if (
            event.button.id is not None
            and event.button.id.startswith("info_action_")
            and self._on_action is not None
        ):
            try:
                index = int(event.button.id.rsplit("_", maxsplit=1)[-1])
            except ValueError:
                return
            if 0 <= index < len(self._actions):
                self._on_action(self._actions[index].command)


class PermissionDialogPane(Static):
    DEFAULT_CSS = """
    PermissionDialogPane {
        border-top: solid $warning;
        background: $boost;
        padding: 1 2 0 2;
        height: auto;
    }

    #permission-scroll {
        max-height: 22;
        min-height: 8;
        border: none;
        padding: 0 1 0 0;
    }

    #permission-actions-inline {
        margin-top: 1;
        height: auto;
    }

    .permission-action {
        margin-right: 1;
        margin-top: 1;
    }

    Button {
        margin-right: 1;
    }
    """

    def __init__(
        self,
        request: PermissionRequestState,
        *,
        on_choice: Callable[[PermissionPromptChoice], None],
    ) -> None:
        super().__init__()
        self._request = request
        self._on_choice = on_choice

    def compose(self) -> ComposeResult:
        target_lines = self._request.target_lines or ["(no specific targets)"]
        lines = [
            self._request.title or f"Permission Request: {self._request.tool_name}",
        ]
        if self._request.subtitle:
            lines.append(self._request.subtitle)
        lines.extend(
            [
                "",
                f"summary: {self._request.summary}",
                f"reason: {self._request.reason or '(none)'}",
            ]
        )
        if self._request.prompt:
            lines.extend(["", self._request.prompt])
        if self._request.detail_lines:
            lines.extend(["", "details:", *[f"- {line}" for line in self._request.detail_lines]])
        lines.extend(["", "targets:", *[f"- {line}" for line in target_lines]])
        if self._request.preview:
            lines.extend(["", "preview:", self._request.preview])
        lines.extend(["", "Choose once, remember for this session, or persist to the project."])
        with VerticalScroll(id="permission-scroll"):
            yield Static("\n".join(lines))
        with Horizontal(id="permission-actions-inline"):
            yield Button("Approve Once", id="allow_once", variant="success", classes="permission-action")
            yield Button("Approve Session", id="allow_session", variant="primary", classes="permission-action")
            yield Button("Allow Project", id="allow_project", variant="default", classes="permission-action")
        with Horizontal(id="permission-actions-inline"):
            yield Button("Deny Once", id="deny_once", variant="warning", classes="permission-action")
            yield Button("Deny Session", id="deny_session", variant="error", classes="permission-action")
            yield Button("Deny Project", id="deny_project", variant="default", classes="permission-action")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        choice = event.button.id
        if choice in {
            "allow_once",
            "allow_session",
            "allow_project",
            "deny_once",
            "deny_session",
            "deny_project",
        }:
            self._on_choice(choice)


class EditorDialogPane(Static):
    DEFAULT_CSS = """
    EditorDialogPane {
        border-top: solid $accent;
        background: $boost;
        padding: 1 2 0 2;
        height: auto;
    }

    #editor-meta {
        color: $text-muted;
        margin-bottom: 1;
    }

    #editor-area {
        height: 16;
        border: none;
    }

    #editor-actions {
        margin-top: 1;
    }
    """

    def __init__(
        self,
        editor: EditorDialogState,
        *,
        on_save: Callable[[str], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__()
        self._editor = editor
        self._on_save = on_save
        self._on_close = on_close

    def compose(self) -> ComposeResult:
        yield Static(self._editor.title)
        yield Static(self._editor.file_path, id="editor-meta")
        yield TextArea(
            self._editor.text,
            id="editor-area",
            language=self._editor.language,
            soft_wrap=True,
        )
        with Horizontal(id="editor-actions"):
            yield Button("Save", id="save_editor", variant="success")
            yield Button("Cancel", id="cancel_editor", variant="default")

    def on_mount(self) -> None:
        self.query_one("#editor-area", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_editor":
            self._on_close()
            return
        if event.button.id == "save_editor":
            text = self.query_one("#editor-area", TextArea).text
            self._on_save(text)


class SelectorDialogPane(Static):
    DEFAULT_CSS = """
    SelectorDialogPane {
        border-top: solid $secondary;
        background: $boost;
        padding: 1 2 0 2;
        height: auto;
    }

    #selector-body {
        height: auto;
    }

    #selector-options {
        width: 2fr;
        min-height: 12;
        max-height: 18;
        border: none;
        margin-right: 1;
    }

    #selector-preview {
        width: 3fr;
        min-height: 12;
        max-height: 18;
        border: none;
        padding: 0 1;
    }

    #selector-actions {
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("enter", "submit_selection", "Select"),
    ]

    def __init__(
        self,
        selector: SelectorDialogState,
        *,
        on_select: Callable[[str], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__()
        self._selector = selector
        self._on_select = on_select
        self._on_close = on_close

    def compose(self) -> ComposeResult:
        yield Static(self._selector.title)
        with Horizontal(id="selector-body"):
            yield OptionList(
                *[
                    Option(
                        option.label,
                        id=f"selector_option_{index}",
                    )
                    for index, option in enumerate(self._selector.options)
                ],
                id="selector-options",
            )
            yield Static("", id="selector-preview")
        with Horizontal(id="selector-actions"):
            yield Button("Select", id="select_selector", variant="success")
            yield Button("Cancel", id="cancel_selector", variant="default")

    def on_mount(self) -> None:
        option_list = self.query_one("#selector-options", OptionList)
        if self._selector.selected_index < len(self._selector.options):
            option_list.highlighted = self._selector.selected_index
        option_list.focus()
        self._refresh_preview(option_list.highlighted)

    def on_option_list_option_highlighted(
        self,
        event: OptionList.OptionHighlighted,
    ) -> None:
        self._refresh_preview(event.option_index)

    def on_option_list_option_selected(
        self,
        event: OptionList.OptionSelected,
    ) -> None:
        self._select_index(event.option_index)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_selector":
            self._on_close()
            return
        if event.button.id == "select_selector":
            option_list = self.query_one("#selector-options", OptionList)
            self._select_index(option_list.highlighted)

    def action_submit_selection(self) -> None:
        option_list = self.query_one("#selector-options", OptionList)
        self._select_index(option_list.highlighted)

    def _refresh_preview(self, index: int | None) -> None:
        if index is None or not (0 <= index < len(self._selector.options)):
            self.query_one("#selector-preview", Static).update("")
            return
        option = self._selector.options[index]
        lines = [option.label]
        if option.description:
            lines.extend(["", option.description])
        if option.preview_lines:
            lines.extend(["", *option.preview_lines])
        self.query_one("#selector-preview", Static).update("\n".join(lines))

    def _select_index(self, index: int | None) -> None:
        if index is None or not (0 <= index < len(self._selector.options)):
            return
        self._on_select(self._selector.options[index].command)
