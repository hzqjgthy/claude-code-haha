from claude_code_py.ui.state.app_state import (
    EditorDialogState,
    InfoDialogState,
    PermissionRequestState,
    PromptMode,
    PromptSuggestionState,
    ReplAppState,
    SelectorDialogState,
    StatusDetailState,
    StatusSnapshot,
    TranscriptEntry,
)


def select_new_transcript_entries(
    state: ReplAppState,
    *,
    since: int,
) -> list[TranscriptEntry]:
    return state.transcript[since:]


def select_status_snapshot(state: ReplAppState) -> StatusSnapshot | None:
    return state.status


def select_status_detail(state: ReplAppState) -> StatusDetailState | None:
    return state.status_detail


def select_task_summary_lines(state: ReplAppState) -> list[str]:
    return list(state.task_summary_lines)


def select_footer_lines(state: ReplAppState) -> list[str]:
    return list(state.footer_lines)


def select_runtime_message(state: ReplAppState) -> str:
    return state.runtime_message


def select_composer_disabled(state: ReplAppState) -> bool:
    return state.is_submitting


def select_info_dialog(state: ReplAppState) -> InfoDialogState | None:
    return state.info_dialog


def select_editor_dialog(state: ReplAppState) -> EditorDialogState | None:
    return state.editor_dialog


def select_selector_dialog(state: ReplAppState) -> SelectorDialogState | None:
    return state.selector_dialog


def select_permission_request(
    state: ReplAppState,
) -> PermissionRequestState | None:
    return state.permission_request


def select_prompt_text(state: ReplAppState) -> str:
    return state.prompt.text


def select_prompt_mode(state: ReplAppState) -> PromptMode:
    return state.prompt.mode


def select_prompt_hints(state: ReplAppState) -> list[str]:
    return list(state.prompt.hints)


def select_prompt_suggestions(
    state: ReplAppState,
) -> list[PromptSuggestionState]:
    return list(state.prompt.suggestions)
