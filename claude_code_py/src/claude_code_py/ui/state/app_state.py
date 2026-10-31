from dataclasses import dataclass, field
from typing import Literal

from claude_code_py.providers.remote import RemoteStatus

TranscriptKind = Literal["system", "user", "assistant", "error"]
InfoDialogKind = str
PromptMode = Literal["prompt", "command"]


@dataclass(slots=True)
class TranscriptEntry:
    kind: TranscriptKind
    text: str


@dataclass(slots=True)
class StatusSnapshot:
    session_id: str
    model: str
    permission_mode: str
    remote_status: RemoteStatus


@dataclass(slots=True)
class PermissionRequestState:
    request_id: str
    tool_name: str
    summary: str
    request_kind: str = "generic"
    title: str | None = None
    subtitle: str | None = None
    prompt: str | None = None
    reason: str | None = None
    target_lines: list[str] = field(default_factory=list)
    detail_lines: list[str] = field(default_factory=list)
    preview: str | None = None


@dataclass(slots=True)
class InfoDialogActionState:
    label: str
    command: str
    description: str | None = None


@dataclass(slots=True)
class EditorDialogState:
    kind: str
    title: str
    file_path: str
    text: str
    language: str = "markdown"


@dataclass(slots=True)
class SelectorOptionState:
    label: str
    command: str
    description: str | None = None
    preview_lines: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SelectorDialogState:
    kind: str
    title: str
    options: list[SelectorOptionState] = field(default_factory=list)
    selected_index: int = 0


@dataclass(slots=True)
class InfoDialogState:
    kind: InfoDialogKind
    title: str
    lines: list[str] = field(default_factory=list)
    actions: list[InfoDialogActionState] = field(default_factory=list)


@dataclass(slots=True)
class PromptSuggestionState:
    value: str
    description: str
    source: str = "command"


@dataclass(slots=True)
class PromptState:
    text: str = ""
    mode: PromptMode = "prompt"
    hints: list[str] = field(default_factory=list)
    suggestions: list[PromptSuggestionState] = field(default_factory=list)
    selected_suggestion: int = 0


@dataclass(slots=True)
class StatusDetailState:
    session_title: str
    project_name: str
    cwd_name: str
    transcript_entries: int = 0
    user_entries: int = 0
    assistant_entries: int = 0
    task_count: int = 0
    command_count: int = 0
    pending_permission_count: int = 0


@dataclass(slots=True)
class ReplAppState:
    transcript: list[TranscriptEntry] = field(default_factory=list)
    status: StatusSnapshot | None = None
    status_detail: StatusDetailState | None = None
    prompt: PromptState = field(default_factory=PromptState)
    task_summary_lines: list[str] = field(default_factory=list)
    footer_lines: list[str] = field(default_factory=list)
    runtime_message: str = "Idle"
    is_submitting: bool = False
    info_dialog: InfoDialogState | None = None
    editor_dialog: EditorDialogState | None = None
    selector_dialog: SelectorDialogState | None = None
    permission_request: PermissionRequestState | None = None
