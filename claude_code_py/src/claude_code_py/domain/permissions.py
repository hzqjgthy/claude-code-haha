from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

PermissionMode = Literal["default", "accept_edits", "bypass_permissions", "plan"]
PermissionModeInput = Literal[
    "default",
    "accept_edits",
    "bypass_permissions",
    "plan",
    "acceptEdits",
    "bypassPermissions",
]
PermissionBehavior = Literal["allow", "ask", "deny"]
PermissionPromptChoice = Literal[
    "allow_once",
    "allow_session",
    "allow_project",
    "deny_once",
    "deny_session",
    "deny_project",
]
PermissionRuleSource = Literal[
    "session", "user_settings", "project_settings", "cli_arg"
]
PermissionMatcherKind = Literal["path", "domain", "command_prefix", "command"]
PermissionRequestKind = Literal[
    "generic",
    "bash",
    "powershell",
    "file_write",
    "file_edit",
    "web_fetch",
    "notebook_edit",
    "ask_user_question",
    "sandbox",
]
ShadowedRuleKind = Literal["ask", "deny"]

_PERMISSION_MODE_ALIASES: dict[str, PermissionMode] = {
    "default": "default",
    "plan": "plan",
    "accept_edits": "accept_edits",
    "acceptEdits": "accept_edits",
    "bypass_permissions": "bypass_permissions",
    "bypassPermissions": "bypass_permissions",
}


def normalize_permission_mode(mode: str | PermissionModeInput) -> PermissionMode:
    normalized = _PERMISSION_MODE_ALIASES.get(mode)
    if normalized is None:
        supported = ", ".join(_PERMISSION_MODE_ALIASES)
        raise ValueError(
            f"Unsupported permission mode '{mode}'. Expected one of: {supported}",
        )
    return normalized


class PermissionTarget(BaseModel):
    tool_name: str
    kind: PermissionMatcherKind | None = None
    value: str | None = None


class PermissionRule(BaseModel):
    source: PermissionRuleSource
    behavior: PermissionBehavior
    tool_name: str
    kind: PermissionMatcherKind | None = None
    pattern: str | None = None


class PermissionContext(BaseModel):
    mode: PermissionMode = "default"
    rules: list[PermissionRule] = Field(default_factory=list)
    ask_mode_enabled: bool = False


class PermissionDecision(BaseModel):
    behavior: PermissionBehavior
    reason: str | None = None
    source: PermissionRuleSource | None = None
    matched_rule: PermissionRule | None = None


class PermissionPromptRequest(BaseModel):
    tool_name: str
    summary: str
    reason: str | None = None
    targets: list[PermissionTarget] = Field(default_factory=list)
    request_kind: PermissionRequestKind = "generic"
    title: str | None = None
    subtitle: str | None = None
    prompt: str | None = None
    detail_lines: list[str] = Field(default_factory=list)
    preview: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _now_utc() -> datetime:
    return datetime.now(UTC)


class PermissionDenialRecord(BaseModel):
    tool_name: str
    summary: str
    reason: str
    request_kind: PermissionRequestKind = "generic"
    targets: list[PermissionTarget] = Field(default_factory=list)
    source: PermissionRuleSource | None = None
    created_at: datetime = Field(default_factory=_now_utc)


class ShadowedPermissionRule(BaseModel):
    rule: PermissionRule
    shadowed_by: PermissionRule
    shadow_type: ShadowedRuleKind
    reason: str
    fix: str
