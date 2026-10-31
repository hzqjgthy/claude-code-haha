from typing import Any

from claude_code_py.app.container import AppContainer
from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.providers.llm.base import LLMProvider
from claude_code_py.providers.remote import RemoteProvider
from claude_code_py.ui.state import (
    AppStateStore,
    EditorDialogState,
    PromptState,
    PromptSuggestionState,
    ReplAppState,
    SelectorDialogState,
)
from claude_code_py.ui.textual.controller import TextualSessionController

_KEEP = object()


class TextualSessionRuntime:
    def __init__(
        self,
        container: AppContainer,
        params: ReplModeParams,
        *,
        provider: LLMProvider | None = None,
        remote_provider: RemoteProvider | None = None,
    ) -> None:
        self._controller = TextualSessionController(
            container,
            params,
            provider=provider,
            remote_provider=remote_provider,
        )
        self._store = AppStateStore(self._snapshot_state())

    @property
    def controller(self) -> TextualSessionController:
        return self._controller

    @property
    def store(self) -> AppStateStore:
        return self._store

    def sync_state(
        self,
        *,
        runtime_message: str | object = _KEEP,
        is_submitting: bool | object = _KEEP,
        info_dialog: Any = _KEEP,
        editor_dialog: Any = _KEEP,
        selector_dialog: Any = _KEEP,
        prompt_state: PromptState | object = _KEEP,
    ) -> ReplAppState:
        current = self._store.get_state()
        next_state = self._snapshot_state(
            runtime_message=(
                current.runtime_message if runtime_message is _KEEP else runtime_message
            ),
            is_submitting=(
                current.is_submitting if is_submitting is _KEEP else is_submitting
            ),
            info_dialog=(current.info_dialog if info_dialog is _KEEP else info_dialog),
            editor_dialog=(
                current.editor_dialog if editor_dialog is _KEEP else editor_dialog
            ),
            selector_dialog=(
                current.selector_dialog
                if selector_dialog is _KEEP
                else selector_dialog
            ),
            prompt_state=(current.prompt if prompt_state is _KEEP else prompt_state),
        )
        return self._store.set_state(next_state)

    def shutdown(self) -> None:
        self._controller.shutdown()

    def _snapshot_state(
        self,
        *,
        runtime_message: str = "Idle",
        is_submitting: bool = False,
        info_dialog=None,
        editor_dialog: EditorDialogState | None = None,
        selector_dialog: SelectorDialogState | None = None,
        prompt_state: PromptState | None = None,
    ) -> ReplAppState:
        return ReplAppState(
            transcript=self._controller.transcript,
            status=self._controller.status_snapshot(),
            status_detail=self._controller.status_detail_snapshot(),
            prompt=prompt_state or PromptState(),
            task_summary_lines=self._controller.task_summary_lines(),
            footer_lines=self._controller.footer_lines(),
            runtime_message=runtime_message,
            is_submitting=is_submitting,
            info_dialog=info_dialog,
            editor_dialog=editor_dialog,
            selector_dialog=selector_dialog,
            permission_request=self._controller.pending_permission_request(),
        )

    def build_prompt_state(
        self,
        text: str,
        *,
        selected_index: int | None = None,
    ) -> PromptState:
        stripped = text.strip()
        if text.startswith("/"):
            body = stripped[1:].strip() if stripped else ""
            command_name = body.split(maxsplit=1)[0] if body else ""
            suggestions = self._controller.command_suggestions(command_name)
            hints = (
                [
                    "Command mode: Enter runs the slash command.",
                    "Type after '/' to filter available commands.",
                ]
                if suggestions
                else [
                    "Command mode: no matching slash commands.",
                    "Use /help to inspect all available commands.",
                ]
            )
            return PromptState(
                text=text,
                mode="command",
                hints=hints,
                suggestions=suggestions,
                selected_suggestion=_clamp_selected_index(
                    selected_index,
                    len(suggestions),
                ),
            )

        suggestions = (
            [
                PromptSuggestionState(
                    value="/help",
                    description="Show available slash commands.",
                    source="builtin",
                ),
                PromptSuggestionState(
                    value="/tasks",
                    description="Inspect current background tasks.",
                    source="builtin",
                ),
            ]
            if not stripped
            else []
        )
        return PromptState(
            text=text,
            mode="prompt",
            hints=[
                "Prompt mode: Enter submits your request.",
                "Start with '/' to browse slash commands.",
            ],
            suggestions=suggestions,
            selected_suggestion=_clamp_selected_index(
                selected_index,
                len(suggestions),
            ),
        )


def _clamp_selected_index(index: int | None, suggestion_count: int) -> int:
    if suggestion_count <= 0:
        return 0
    if index is None:
        return 0
    return max(0, min(index, suggestion_count - 1))
