from claude_code_py.ui.state import (
    AppStateStore,
    InfoDialogState,
    ReplAppState,
    TranscriptEntry,
    select_composer_disabled,
    select_footer_lines,
    select_info_dialog,
    select_new_transcript_entries,
    select_runtime_message,
    select_task_summary_lines,
)


def test_app_state_store_updates_and_notifies() -> None:
    store = AppStateStore(ReplAppState(runtime_message="Idle"))
    seen: list[str] = []

    unsubscribe = store.subscribe(lambda state: seen.append(state.runtime_message))

    store.update(lambda state: ReplAppState(runtime_message="Running"))
    unsubscribe()
    store.update(lambda state: ReplAppState(runtime_message="Done"))

    assert store.get_state().runtime_message == "Done"
    assert seen == ["Running"]


def test_ui_state_selectors_return_expected_views() -> None:
    state = ReplAppState(
        transcript=[
            TranscriptEntry("system", "boot"),
            TranscriptEntry("user", "hello"),
            TranscriptEntry("assistant", "world"),
        ],
        task_summary_lines=["task-1"],
        footer_lines=["line-a", "line-b"],
        runtime_message="Idle",
        is_submitting=True,
        info_dialog=InfoDialogState(
            kind="help",
            title="Command Help",
            lines=["/help"],
        ),
    )

    assert [entry.text for entry in select_new_transcript_entries(state, since=1)] == [
        "hello",
        "world",
    ]
    assert select_task_summary_lines(state) == ["task-1"]
    assert select_footer_lines(state) == ["line-a", "line-b"]
    assert select_runtime_message(state) == "Idle"
    assert select_composer_disabled(state) is True
    assert select_info_dialog(state) is not None
    assert select_info_dialog(state).title == "Command Help"  # type: ignore[union-attr]
