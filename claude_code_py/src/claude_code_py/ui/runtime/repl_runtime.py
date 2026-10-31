from pathlib import Path

from claude_code_py.app.container import AppContainer
from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.domain.permissions import PermissionPromptChoice
from claude_code_py.providers.llm.base import LLMProvider
from claude_code_py.providers.remote import RemoteProvider
from claude_code_py.ui.runtime.session_runtime import TextualSessionRuntime
from claude_code_py.ui.state import InfoDialogState


class TextualReplRuntime:
    def __init__(
        self,
        container: AppContainer,
        params: ReplModeParams,
        *,
        provider: LLMProvider | None = None,
        remote_provider: RemoteProvider | None = None,
    ) -> None:
        self._session_runtime = TextualSessionRuntime(
            container,
            params,
            provider=provider,
            remote_provider=remote_provider,
        )

    @property
    def store(self):
        return self._session_runtime.store

    @property
    def controller(self):
        return self._session_runtime.controller

    @property
    def terminate_requested(self) -> bool:
        return self.controller.terminate_requested

    def refresh(self):
        self.controller.drain_background_events()
        prompt = self.store.get_state().prompt
        return self._session_runtime.sync_state(
            prompt_state=self._session_runtime.build_prompt_state(
                prompt.text,
                selected_index=prompt.selected_suggestion,
            ),
        )

    def show_help(self):
        return self._session_runtime.sync_state(
            info_dialog=InfoDialogState(
                kind="help",
                title="Command Help",
                lines=self.controller.command_help_lines(),
            )
        )

    def show_policy(self):
        return self._session_runtime.sync_state(
            info_dialog=InfoDialogState(
                kind="policy",
                title="Permission Policy",
                lines=self.controller.permission_summary_lines(),
            )
        )

    def show_latest_task(self):
        return self._session_runtime.sync_state(
            info_dialog=InfoDialogState(
                kind="task_detail",
                title="Latest Task",
                lines=self.controller.task_detail_lines(),
            )
        )

    def show_remote(self):
        return self._session_runtime.sync_state(
            info_dialog=InfoDialogState(
                kind="remote",
                title="Remote Status",
                lines=self.controller.remote_summary_lines(),
            )
        )

    def clear_info_dialog(self):
        return self._session_runtime.sync_state(info_dialog=None)

    def clear_editor_dialog(self):
        return self._session_runtime.sync_state(editor_dialog=None)

    def clear_selector_dialog(self):
        return self._session_runtime.sync_state(selector_dialog=None)

    def update_prompt_text(self, text: str):
        current_prompt = self.store.get_state().prompt
        return self._session_runtime.sync_state(
            prompt_state=self._session_runtime.build_prompt_state(
                text,
                selected_index=current_prompt.selected_suggestion,
            ),
        )

    def cycle_prompt_suggestion(self, direction: int):
        prompt = self.store.get_state().prompt
        if not prompt.suggestions:
            return self.store.get_state()
        next_index = (prompt.selected_suggestion + direction) % len(prompt.suggestions)
        return self._session_runtime.sync_state(
            prompt_state=self._session_runtime.build_prompt_state(
                prompt.text,
                selected_index=next_index,
            ),
        )

    def apply_selected_prompt_suggestion(self) -> str:
        prompt = self.store.get_state().prompt
        if not prompt.suggestions:
            return prompt.text
        selection = prompt.suggestions[prompt.selected_suggestion].value
        next_text = selection
        if prompt.mode == "command" and not next_text.endswith(" "):
            next_text = f"{next_text} "
        self._session_runtime.sync_state(
            prompt_state=self._session_runtime.build_prompt_state(next_text),
        )
        return next_text

    def submit_prompt(self, prompt: str):
        self._session_runtime.sync_state(
            runtime_message=f"Running: {prompt[:48]}",
            is_submitting=True,
            prompt_state=self._session_runtime.build_prompt_state(prompt),
        )
        try:
            result = self.controller.submit_prompt(prompt)
        except Exception as exc:
            self.controller.append_ui_entry("error", str(exc))
            self._session_runtime.sync_state(
                runtime_message=f"Error: {exc}",
                is_submitting=False,
                prompt_state=self._session_runtime.build_prompt_state(""),
            )
            return []
        requested_dialog = self.controller.consume_requested_info_dialog()
        requested_editor = self.controller.consume_requested_editor_dialog()
        requested_selector = self.controller.consume_requested_selector_dialog()
        next_info_dialog = (
            None
            if requested_editor is not None or requested_selector is not None
            else requested_dialog
        )
        self._session_runtime.sync_state(
            runtime_message="Idle",
            is_submitting=False,
            prompt_state=self._session_runtime.build_prompt_state(""),
            info_dialog=next_info_dialog,
            editor_dialog=requested_editor,
            selector_dialog=None if requested_editor is not None else requested_selector,
        )
        return result

    def save_editor_dialog(self, text: str):
        editor = self.store.get_state().editor_dialog
        if editor is None:
            return self.store.get_state()

        path = Path(editor.file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.controller.append_ui_entry("system", f"Saved file: {path}")
        return self._session_runtime.sync_state(
            runtime_message="Idle",
            editor_dialog=None,
        )

    def resolve_permission_request(self, choice: PermissionPromptChoice):
        self.controller.resolve_permission_request(choice)
        return self._session_runtime.sync_state()

    def shutdown(self):
        self._session_runtime.shutdown()
