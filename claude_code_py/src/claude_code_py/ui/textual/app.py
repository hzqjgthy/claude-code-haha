import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual import events
from textual.widgets import Input

from claude_code_py.app.container import AppContainer
from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.common.clipboard import ClipboardError, copy_text_to_clipboard
from claude_code_py.domain.permissions import PermissionPromptChoice
from claude_code_py.providers.llm.base import LLMProvider
from claude_code_py.providers.remote import RemoteProvider
from claude_code_py.ui.layout import ModalManager, OverlayManager, ReplFullscreenLayout
from claude_code_py.ui.runtime import TextualReplRuntime
from claude_code_py.ui.state import (
    PermissionRequestState,
    ReplAppState,
    select_composer_disabled,
    select_editor_dialog,
    select_footer_lines,
    select_info_dialog,
    select_new_transcript_entries,
    select_permission_request,
    select_selector_dialog,
    select_runtime_message,
    select_status_detail,
    select_status_snapshot,
    select_task_summary_lines,
)
from claude_code_py.ui.textual.dialogs import (
    EditorDialogPane,
    InfoDialogPane,
    PermissionDialogPane,
    SelectorDialogPane,
)


class ClaudeCodeTextualApp(App[int]):
    CSS = """
    Screen {
        background: rgb(0,0,0);
        color: rgb(255,255,255);
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+o", "toggle_transcript_focus", "Transcript"),
        Binding("f6", "copy_visible_text", "Copy"),
        Binding("ctrl+shift+c", "copy_visible_text", "Copy", show=False),
        Binding("ctrl+y", "copy_visible_text", "Copy", show=False),
        Binding("escape", "close_layer", "Close"),
        Binding("f1", "show_help", "Help"),
        Binding("f2", "show_policy", "Policy"),
        Binding("f3", "show_latest_task", "Latest Task"),
        Binding("f4", "show_remote", "Remote"),
        Binding("f5", "refresh_runtime", "Refresh"),
    ]

    def __init__(
        self,
        container: AppContainer,
        params: ReplModeParams,
        *,
        provider: LLMProvider | None = None,
        remote_provider: RemoteProvider | None = None,
    ) -> None:
        super().__init__()
        self._params = params
        self._runtime = TextualReplRuntime(
            container,
            params,
            provider=provider,
            remote_provider=remote_provider,
        )
        self._rendered_entries = 0
        self._overlay_manager = OverlayManager()
        self._modal_manager = ModalManager()

    def compose(self) -> ComposeResult:
        yield ReplFullscreenLayout(id="fullscreen-layout")

    def on_mount(self) -> None:
        self.title = "claude-code-py"
        self.sub_title = "Textual session"
        self._refresh_runtime()
        self.set_interval(0.5, self._refresh_runtime)
        composer = self.query_one(ReplFullscreenLayout).prompt_composer()
        composer.set_suggestion_handlers(
            on_cycle=self._on_prompt_suggestion_cycle,
            on_apply=self._on_prompt_suggestion_apply,
        )
        composer.focus_input()
        if self._params.initial_prompt:
            asyncio.create_task(self._submit_prompt(self._params.initial_prompt))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        self.query_one(ReplFullscreenLayout).prompt_composer().clear()
        if not prompt or select_composer_disabled(self._runtime.store.get_state()):
            return
        await self._submit_prompt(prompt)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "composer-input":
            return
        self._runtime.update_prompt_text(event.value)
        self._refresh_prompt_state(self._runtime.store.get_state())

    def on_key(self, event: events.Key) -> None:
        layout = self.query_one(ReplFullscreenLayout)
        transcript = layout.transcript_widget()
        if self.focused is transcript.search_input_widget():
            if event.key == "escape":
                transcript.close_search(clear_query=False, refocus_log=True)
                event.stop()
                return
        if self.focused is transcript.log_widget():
            if event.key == "slash":
                transcript.open_search()
                event.stop()
                return
            if event.character == "n":
                transcript.next_search_match()
                event.stop()
                return
            if event.character == "N":
                transcript.previous_search_match()
                event.stop()
                return

    def action_show_help(self) -> None:
        self._runtime.show_help()
        self._sync_dialogs()

    def action_show_policy(self) -> None:
        self._runtime.show_policy()
        self._sync_dialogs()

    def action_show_latest_task(self) -> None:
        self._runtime.show_latest_task()
        self._sync_dialogs()

    def action_show_remote(self) -> None:
        self._runtime.show_remote()
        self._sync_dialogs()

    def action_refresh_runtime(self) -> None:
        self._refresh_runtime()

    def action_close_layer(self) -> None:
        transcript = self.query_one(ReplFullscreenLayout).transcript_widget()
        if transcript.is_search_open():
            transcript.close_search(clear_query=False, refocus_log=True)
            return
        state = self._runtime.store.get_state()
        if select_permission_request(state) is not None:
            self._on_permission_choice("deny_once")
            return
        if select_editor_dialog(state) is not None:
            self._on_editor_dialog_close()
            return
        if select_selector_dialog(state) is not None:
            self._on_selector_dialog_close()
            return
        if select_info_dialog(state) is not None:
            self._on_info_dialog_close()

    def action_quit(self) -> None:
        self.exit(0)

    def action_toggle_transcript_focus(self) -> None:
        layout = self.query_one(ReplFullscreenLayout)
        transcript = layout.transcript_widget()
        if self.focused is transcript.log_widget() or self.focused is transcript.search_input_widget():
            layout.prompt_composer().focus_input()
            return
        transcript.focus_log()

    def action_copy_visible_text(self) -> None:
        state = self._runtime.store.get_state()
        transcript = self.query_one(ReplFullscreenLayout).transcript_widget()
        label, content = _build_copy_payload(
            state,
            transcript.export_plain_text(),
        )
        if not content.strip():
            self.notify(
                "Nothing to copy yet.",
                title="Clipboard",
                severity="warning",
            )
            return
        try:
            backend = copy_text_to_clipboard(
                content,
                osc52_fallback=self.copy_to_clipboard,
            )
        except ClipboardError as exc:
            self.notify(str(exc), title="Clipboard", severity="error")
            return
        self.notify(
            f"Copied {label} to clipboard via {backend}.",
            title="Clipboard",
        )

    def shutdown_runtime(self) -> None:
        self._runtime.shutdown()

    def _on_prompt_suggestion_cycle(self, direction: int) -> None:
        prompt = self._runtime.store.get_state().prompt
        if not prompt.suggestions:
            return
        self._runtime.cycle_prompt_suggestion(direction)
        self._refresh_prompt_state(self._runtime.store.get_state())

    def _on_prompt_suggestion_apply(self) -> str:
        prompt = self._runtime.store.get_state().prompt
        if not prompt.suggestions:
            return prompt.text
        next_text = self._runtime.apply_selected_prompt_suggestion()
        self._refresh_prompt_state(self._runtime.store.get_state())
        return next_text

    async def _submit_prompt(self, prompt: str) -> None:
        if select_composer_disabled(self._runtime.store.get_state()):
            return
        await asyncio.to_thread(self._runtime.submit_prompt, prompt)
        if self._runtime.terminate_requested:
            self.exit(0)
            return
        self.query_one(ReplFullscreenLayout).prompt_composer().focus_input()
        self._refresh_runtime()

    def _refresh_runtime(self) -> None:
        self._runtime.refresh()
        state = self._runtime.store.get_state()
        self._refresh_transcript()
        self._refresh_prompt_chrome(state)
        self._refresh_prompt_state(state)
        self._refresh_composer_disabled(state)
        self._sync_dialogs(state)

    def _refresh_transcript(self) -> None:
        state = self._runtime.store.get_state()
        transcript_widget = self.query_one(ReplFullscreenLayout).transcript_widget()
        transcript_widget.update_context(
            status=select_status_snapshot(state),
            detail=select_status_detail(state),
            runtime_message=select_runtime_message(state),
            permission_request=select_permission_request(state),
            task_summary_lines=select_task_summary_lines(state),
        )
        if len(state.transcript) < self._rendered_entries:
            transcript_widget.replace_entries(state.transcript)
            self._rendered_entries = len(state.transcript)
            return
        new_entries = select_new_transcript_entries(
            state,
            since=self._rendered_entries,
        )
        transcript_widget.append_entries(new_entries)
        self._rendered_entries += len(new_entries)

    def _refresh_prompt_chrome(self, state) -> None:
        layout = self.query_one(ReplFullscreenLayout)
        composer = layout.prompt_composer()
        composer.update_status(
            select_status_snapshot(state),
            select_status_detail(state),
            select_runtime_message(state),
            select_task_summary_lines(state),
        )
        composer.update_footer(select_footer_lines(state))
        self._refresh_prompt_overlay(state)

    def _refresh_prompt_overlay(self, state) -> None:
        layout = self.query_one(ReplFullscreenLayout)
        layout.prompt_overlay_widget().update_state(prompt=state.prompt)

    def _refresh_prompt_state(self, state) -> None:
        self.query_one(ReplFullscreenLayout).prompt_composer().update_prompt_state(
            state.prompt
        )
        self._refresh_prompt_overlay(state)

    def _refresh_composer_disabled(self, state) -> None:
        self.query_one(ReplFullscreenLayout).prompt_composer().set_disabled(
            select_composer_disabled(state)
        )

    def _sync_dialogs(self, state=None) -> None:
        state = state or self._runtime.store.get_state()
        layout = self.query_one(ReplFullscreenLayout)
        editor_dialog = select_editor_dialog(state)
        if editor_dialog is not None:
            editor_key = f"{editor_dialog.kind}:{editor_dialog.file_path}"
            if self._modal_manager.should_present(editor_key):
                self._modal_manager.mark_presented(editor_key)
                layout.set_modal(
                    EditorDialogPane(
                        editor_dialog,
                        on_save=self._on_editor_dialog_save,
                        on_close=self._on_editor_dialog_close,
                    ),
                )
            return

        selector_dialog = select_selector_dialog(state)
        if selector_dialog is not None:
            selector_key = selector_dialog.kind
            if self._modal_manager.should_present(selector_key):
                self._modal_manager.mark_presented(selector_key)
                layout.set_modal(
                    SelectorDialogPane(
                        selector_dialog,
                        on_select=self._on_selector_dialog_select,
                        on_close=self._on_selector_dialog_close,
                    ),
                )
            return

        info_dialog = select_info_dialog(state)
        if info_dialog is None:
            self._modal_manager.clear()
            layout.clear_modal()
        elif self._modal_manager.should_present(info_dialog.kind):
            self._modal_manager.mark_presented(info_dialog.kind)
            layout.set_modal(
                InfoDialogPane(
                    info_dialog.title,
                    info_dialog.lines,
                    on_close=self._on_info_dialog_close,
                    actions=info_dialog.actions,
                    on_action=self._on_info_dialog_action,
                ),
            )

        request = select_permission_request(state)
        if request is None:
            self._overlay_manager.clear()
            layout.clear_overlay()
            return
        if not self._overlay_manager.should_present(request.request_id):
            return

        self._overlay_manager.mark_presented(request.request_id)
        layout.set_overlay(
            PermissionDialogPane(
                request,
                on_choice=self._on_permission_choice,
            ),
        )

    def _on_info_dialog_close(self) -> None:
        self._modal_manager.clear()
        self.query_one(ReplFullscreenLayout).clear_modal()
        self._runtime.clear_info_dialog()
        self._refresh_runtime()

    def _on_info_dialog_action(self, command: str) -> None:
        self._modal_manager.clear()
        self.query_one(ReplFullscreenLayout).clear_modal()
        self._runtime.clear_info_dialog()
        self.query_one(ReplFullscreenLayout).prompt_composer().clear()
        asyncio.create_task(self._submit_prompt(command))

    def _on_editor_dialog_close(self) -> None:
        self._modal_manager.clear()
        self.query_one(ReplFullscreenLayout).clear_modal()
        self._runtime.clear_editor_dialog()
        self._refresh_runtime()

    def _on_editor_dialog_save(self, text: str) -> None:
        self._modal_manager.clear()
        self.query_one(ReplFullscreenLayout).clear_modal()
        self._runtime.save_editor_dialog(text)
        self._refresh_runtime()

    def _on_selector_dialog_close(self) -> None:
        self._modal_manager.clear()
        self.query_one(ReplFullscreenLayout).clear_modal()
        self._runtime.clear_selector_dialog()
        self._refresh_runtime()

    def _on_selector_dialog_select(self, command: str) -> None:
        self._modal_manager.clear()
        self.query_one(ReplFullscreenLayout).clear_modal()
        self._runtime.clear_selector_dialog()
        self.query_one(ReplFullscreenLayout).prompt_composer().clear()
        asyncio.create_task(self._submit_prompt(command))

    def _on_permission_choice(self, choice: PermissionPromptChoice) -> None:
        self._runtime.resolve_permission_request(choice)
        self._overlay_manager.clear()
        self.query_one(ReplFullscreenLayout).clear_overlay()
        self._refresh_runtime()


def _build_copy_payload(
    state: ReplAppState,
    transcript_text: str,
) -> tuple[str, str]:
    if state.permission_request is not None:
        return "permission request", _render_permission_request_text(
            state.permission_request,
        )
    if state.editor_dialog is not None:
        editor = state.editor_dialog
        return "editor", "\n".join(
            [editor.title, editor.file_path, "", editor.text]
        ).strip()
    if state.selector_dialog is not None:
        return "selector", _render_selector_dialog_text(state)
    if state.info_dialog is not None:
        return "panel", _render_info_dialog_text(state)
    return "transcript", transcript_text


def _render_info_dialog_text(state: ReplAppState) -> str:
    assert state.info_dialog is not None
    lines = [state.info_dialog.title, "", *state.info_dialog.lines]
    if state.info_dialog.actions:
        lines.extend(["", "Actions:"])
        lines.extend(
            f"- {action.label}: {action.command}"
            for action in state.info_dialog.actions
        )
    return "\n".join(lines).strip()


def _render_selector_dialog_text(state: ReplAppState) -> str:
    assert state.selector_dialog is not None
    selector = state.selector_dialog
    lines = [selector.title, ""]
    for index, option in enumerate(selector.options):
        marker = ">" if index == selector.selected_index else "-"
        lines.append(f"{marker} {option.label}")
        if option.description:
            lines.append(f"  {option.description}")
        if option.preview_lines:
            lines.extend(f"  {line}" for line in option.preview_lines)
        lines.append("")
    return "\n".join(lines).strip()


def _render_permission_request_text(request: PermissionRequestState) -> str:
    target_lines = request.target_lines or ["(no specific targets)"]
    lines = [
        request.title or f"Permission Request: {request.tool_name}",
    ]
    if request.subtitle:
        lines.append(request.subtitle)
    lines.extend(
        [
            "",
            f"summary: {request.summary}",
            f"reason: {request.reason or '(none)'}",
        ]
    )
    if request.prompt:
        lines.extend(["", request.prompt])
    if request.detail_lines:
        lines.extend(["", "details:", *[f"- {line}" for line in request.detail_lines]])
    lines.extend(["", "targets:", *[f"- {line}" for line in target_lines]])
    if request.preview:
        lines.extend(["", "preview:", request.preview])
    return "\n".join(lines).strip()
