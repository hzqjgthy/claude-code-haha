from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from claude_code_py.common.json import from_json, to_json


def _now_utc() -> datetime:
    return datetime.now(UTC)


class RuntimePreferences(BaseModel):
    theme: str = "dark"
    output_style: str = "default"
    voice_enabled: bool = False
    editor_mode: str = "normal"
    fast_mode: bool = False
    effort_level: str | None = None
    advisor_model: str | None = None
    copy_full_response: bool = False
    statusline_enabled: bool = False
    chrome_enabled_by_default: bool = False
    terminal_setup_complete: bool = False
    extra_usage_enabled: bool = False
    has_visited_passes: bool = False
    default_remote_environment: str | None = None
    ide_auto_connect: bool = False
    preferred_ide: str | None = None
    sandbox_enabled: bool = False
    sandbox_auto_allow: bool = False
    sandbox_allow_unsandboxed_fallback: bool = False


class SessionUsageSnapshot(BaseModel):
    session_id: str
    started_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    request_count: int = 0
    total_duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    total_cost_usd: float = 0.0
    priced_request_count: int = 0
    unpriced_request_count: int = 0
    last_model: str | None = None


class RuntimeStateDocument(BaseModel):
    preferences: RuntimePreferences = Field(default_factory=RuntimePreferences)
    session_tags: dict[str, str] = Field(default_factory=dict)
    session_colors: dict[str, str] = Field(default_factory=dict)
    backgrounded_sessions: dict[str, bool] = Field(default_factory=dict)
    trusted_plugins: dict[str, bool] = Field(default_factory=dict)
    session_usage: dict[str, SessionUsageSnapshot] = Field(default_factory=dict)


class RuntimeStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def get_preferences(self) -> RuntimePreferences:
        return self._load().preferences.model_copy(deep=True)

    def update_preferences(self, **changes: object) -> RuntimePreferences:
        document = self._load()
        updated = document.preferences.model_copy(update=changes)
        document.preferences = updated
        self._save(document)
        return updated.model_copy(deep=True)

    def get_session_tag(self, session_id: str) -> str | None:
        tag = self._load().session_tags.get(session_id)
        return tag or None

    def set_session_tag(self, session_id: str, tag: str | None) -> None:
        document = self._load()
        normalized = (tag or "").strip()
        if normalized:
            document.session_tags[session_id] = normalized
        else:
            document.session_tags.pop(session_id, None)
        self._save(document)

    def list_session_tags(self) -> dict[str, str]:
        return dict(self._load().session_tags)

    def is_session_backgrounded(self, session_id: str) -> bool:
        return bool(self._load().backgrounded_sessions.get(session_id))

    def set_session_backgrounded(self, session_id: str, backgrounded: bool) -> None:
        document = self._load()
        if backgrounded:
            document.backgrounded_sessions[session_id] = True
        else:
            document.backgrounded_sessions.pop(session_id, None)
        self._save(document)

    def list_backgrounded_sessions(self) -> dict[str, bool]:
        return {
            session_id: True
            for session_id, backgrounded in self._load().backgrounded_sessions.items()
            if backgrounded
        }

    def is_plugin_trusted(self, plugin_key: str) -> bool:
        return bool(self._load().trusted_plugins.get(plugin_key))

    def set_plugin_trusted(self, plugin_key: str, trusted: bool) -> None:
        document = self._load()
        if trusted:
            document.trusted_plugins[plugin_key] = True
        else:
            document.trusted_plugins.pop(plugin_key, None)
        self._save(document)

    def list_trusted_plugins(self) -> dict[str, bool]:
        return dict(self._load().trusted_plugins)

    def get_session_color(self, session_id: str) -> str | None:
        color = self._load().session_colors.get(session_id)
        return color or None

    def set_session_color(self, session_id: str, color: str | None) -> None:
        document = self._load()
        normalized = (color or "").strip().lower()
        if normalized and normalized != "default":
            document.session_colors[session_id] = normalized
        else:
            document.session_colors.pop(session_id, None)
        self._save(document)

    def list_session_usage(self) -> list[SessionUsageSnapshot]:
        return sorted(
            [
                usage.model_copy(deep=True)
                for usage in self._load().session_usage.values()
            ],
            key=lambda usage: usage.updated_at,
            reverse=True,
        )

    def get_session_usage(self, session_id: str) -> SessionUsageSnapshot | None:
        usage = self._load().session_usage.get(session_id)
        return usage.model_copy(deep=True) if usage is not None else None

    def record_session_usage(
        self,
        session_id: str,
        *,
        model: str,
        raw_response: dict[str, Any],
        duration_ms: int,
    ) -> SessionUsageSnapshot:
        document = self._load()
        usage = document.session_usage.get(session_id) or SessionUsageSnapshot(
            session_id=session_id,
        )
        tokens = _extract_usage(raw_response)
        estimated_cost = estimate_usage_cost_usd(model, tokens)
        usage = usage.model_copy(
            update={
                "updated_at": _now_utc(),
                "request_count": usage.request_count + 1,
                "total_duration_ms": usage.total_duration_ms + max(duration_ms, 0),
                "input_tokens": usage.input_tokens + tokens["input_tokens"],
                "output_tokens": usage.output_tokens + tokens["output_tokens"],
                "cache_creation_input_tokens": (
                    usage.cache_creation_input_tokens
                    + tokens["cache_creation_input_tokens"]
                ),
                "cache_read_input_tokens": (
                    usage.cache_read_input_tokens
                    + tokens["cache_read_input_tokens"]
                ),
                "total_cost_usd": (
                    usage.total_cost_usd + estimated_cost
                    if estimated_cost is not None
                    else usage.total_cost_usd
                ),
                "priced_request_count": (
                    usage.priced_request_count + 1
                    if estimated_cost is not None
                    else usage.priced_request_count
                ),
                "unpriced_request_count": (
                    usage.unpriced_request_count
                    if estimated_cost is not None
                    else usage.unpriced_request_count + 1
                ),
                "last_model": model,
            },
        )
        document.session_usage[session_id] = usage
        self._save(document)
        return usage.model_copy(deep=True)

    def _load(self) -> RuntimeStateDocument:
        if not self._path.exists():
            return RuntimeStateDocument()
        try:
            raw = from_json(self._path.read_text(encoding="utf-8"))
        except Exception:
            return RuntimeStateDocument()
        try:
            return RuntimeStateDocument.model_validate(raw)
        except Exception:
            return RuntimeStateDocument()

    def _save(self, document: RuntimeStateDocument) -> None:
        self._path.write_text(
            to_json(document.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )


def estimate_usage_cost_usd(
    model: str,
    usage: dict[str, int],
) -> float | None:
    pricing = _resolve_model_pricing(model)
    if pricing is None:
        return None
    return (
        (usage["input_tokens"] / 1_000_000) * pricing["input_tokens"]
        + (usage["output_tokens"] / 1_000_000) * pricing["output_tokens"]
        + (usage["cache_read_input_tokens"] / 1_000_000)
        * pricing["cache_read_input_tokens"]
        + (usage["cache_creation_input_tokens"] / 1_000_000)
        * pricing["cache_creation_input_tokens"]
    )


def _extract_usage(raw_response: dict[str, Any]) -> dict[str, int]:
    usage = raw_response.get("usage")
    if not isinstance(usage, dict):
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
    return {
        "input_tokens": _coerce_int(usage.get("input_tokens")),
        "output_tokens": _coerce_int(usage.get("output_tokens")),
        "cache_creation_input_tokens": _coerce_int(
            usage.get("cache_creation_input_tokens"),
        ),
        "cache_read_input_tokens": _coerce_int(usage.get("cache_read_input_tokens")),
    }


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _resolve_model_pricing(model: str) -> dict[str, float] | None:
    normalized = model.strip().lower()
    tiers = [
        (
            ("haiku-3-5", "claude-3-5-haiku", "claude-3-5-haiku-latest"),
            {
                "input_tokens": 0.8,
                "output_tokens": 4.0,
                "cache_creation_input_tokens": 1.0,
                "cache_read_input_tokens": 0.08,
            },
        ),
        (
            ("haiku-4-5", "claude-haiku-4-5", "claude-haiku-4-5-latest"),
            {
                "input_tokens": 1.0,
                "output_tokens": 5.0,
                "cache_creation_input_tokens": 1.25,
                "cache_read_input_tokens": 0.1,
            },
        ),
        (
            (
                "sonnet-3-5",
                "sonnet-3-7",
                "sonnet-4",
                "sonnet-4-5",
                "sonnet-4-6",
                "claude-sonnet",
                "claude-3-7-sonnet",
                "claude-sonnet-4",
                "claude-sonnet-4-5",
                "claude-sonnet-4-6",
            ),
            {
                "input_tokens": 3.0,
                "output_tokens": 15.0,
                "cache_creation_input_tokens": 3.75,
                "cache_read_input_tokens": 0.3,
            },
        ),
        (
            ("opus-4", "opus-4-1", "claude-opus-4", "claude-opus-4-1"),
            {
                "input_tokens": 15.0,
                "output_tokens": 75.0,
                "cache_creation_input_tokens": 18.75,
                "cache_read_input_tokens": 1.5,
            },
        ),
        (
            ("opus-4-5", "opus-4-6", "claude-opus-4-5", "claude-opus-4-6"),
            {
                "input_tokens": 5.0,
                "output_tokens": 25.0,
                "cache_creation_input_tokens": 6.25,
                "cache_read_input_tokens": 0.5,
            },
        ),
    ]
    for names, pricing in tiers:
        if any(name in normalized for name in names):
            return pricing
    return None
