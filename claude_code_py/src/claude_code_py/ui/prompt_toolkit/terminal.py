from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ReplStatus:
    session_id: str
    model: str
    permission_mode: str


class PromptToolkitReplTerminal:
    def __init__(self, *, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._status: ReplStatus | None = None
        self._session = self._build_session()

    def bind_status(self, status: ReplStatus) -> None:
        self._status = status

    def show_welcome(self) -> None:
        self._print_text(
            (
                "Interactive REPL ready.\n"
                "Submit with Esc+Enter. Insert newlines with Enter. Exit with Ctrl+D.\n"
            ),
        )
        if self._status is not None:
            self.show_system(
                " | ".join(
                    [
                        f"session={self._status.session_id}",
                        f"model={self._status.model}",
                        f"permission_mode={self._status.permission_mode}",
                    ],
                ),
            )

    def show_system(self, text: str) -> None:
        self._print_text(f"[system] {text}")

    def show_assistant(self, text: str) -> None:
        self._print_text(f"\nClaude\n{text}\n")

    def show_error(self, text: str) -> None:
        self._print_text(f"[error] {text}")

    def show_interrupt(self) -> None:
        self._print_text("[interrupt] Request interrupted. Session state was preserved.")

    def show_goodbye(self) -> None:
        self._print_text("Leaving REPL.")

    def read_prompt(self) -> str | None:
        try:
            return self._session.prompt(self._prompt_prefix)
        except EOFError:
            return None

    def _build_session(self) -> Any:
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.key_binding import KeyBindings
            from prompt_toolkit.styles import Style
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Interactive mode requires prompt_toolkit. "
                "Run `pip install -e \".[dev]\"` or update the conda environment.",
            ) from exc

        history_path = self._data_dir / "repl_history.txt"
        history_path.parent.mkdir(parents=True, exist_ok=True)

        key_bindings = KeyBindings()

        @key_bindings.add("escape", "enter")
        def _(event) -> None:
            event.current_buffer.validate_and_handle()

        style = Style.from_dict(
            {
                "prompt": "ansicyan bold",
                "toolbar": "bg:#1f2937 #e5e7eb",
            },
        )

        return PromptSession(
            multiline=True,
            history=FileHistory(str(history_path)),
            key_bindings=key_bindings,
            prompt_continuation=lambda width, line_number, is_soft_wrap: "... ",
            bottom_toolbar=self._bottom_toolbar,
            style=style,
        )

    @property
    def _prompt_prefix(self) -> str:
        session_label = self._status.session_id[:8] if self._status else "session"
        return f"{session_label}> "

    def _bottom_toolbar(self) -> list[tuple[str, str]]:
        if self._status is None:
            return [("class:toolbar", " Esc+Enter send | Ctrl+D exit ")]
        return [
            (
                "class:toolbar",
                (
                    f" session={self._status.session_id} "
                    f"| model={self._status.model} "
                    f"| mode={self._status.permission_mode} "
                    "| Esc+Enter send | Ctrl+D exit "
                ),
            ),
        ]

    @staticmethod
    def _print_text(text: str) -> None:
        print(text, flush=True)
