from datetime import UTC, datetime

from claude_code_py.domain.messages import AssistantMessage, Message, UserMessage
from claude_code_py.domain.sessions import SessionMetadata, SessionSummary

TITLE_MAX_LENGTH = 80
PREVIEW_MAX_LENGTH = 120


def _trim_text(value: str, *, limit: int) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def choose_session_title(metadata: SessionMetadata, messages: list[Message]) -> str:
    if metadata.title and metadata.title != "Untitled session":
        return metadata.title
    first_user = first_user_message(messages)
    if first_user:
        return _trim_text(first_user.content, limit=TITLE_MAX_LENGTH)
    return metadata.title


def first_user_message(messages: list[Message]) -> UserMessage | None:
    for message in messages:
        if isinstance(message, UserMessage):
            return message
    return None


def last_user_message(messages: list[Message]) -> UserMessage | None:
    for message in reversed(messages):
        if isinstance(message, UserMessage):
            return message
    return None


def last_assistant_message(messages: list[Message]) -> AssistantMessage | None:
    for message in reversed(messages):
        if isinstance(message, AssistantMessage):
            return message
    return None


def summarize_session(
    metadata: SessionMetadata,
    messages: list[Message],
    *,
    transcript_path: str,
) -> SessionSummary:
    first_user = first_user_message(messages)
    last_user = last_user_message(messages)
    last_assistant = last_assistant_message(messages)
    title = choose_session_title(metadata, messages)
    return SessionSummary(
        session_id=metadata.session_id,
        title=title,
        status=metadata.status,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
        message_count=len(messages),
        first_user_message=_trim_optional(first_user.content if first_user else None),
        last_user_message=_trim_optional(last_user.content if last_user else None),
        last_assistant_message=_trim_optional(
            last_assistant.content if last_assistant else None,
        ),
        transcript_path=transcript_path,
        parent_session_id=metadata.parent_session_id,
    )


def touch_metadata(
    metadata: SessionMetadata,
    messages: list[Message],
    *,
    status: str,
    updated_at: datetime | None = None,
) -> SessionMetadata:
    timestamp = updated_at or datetime.now(UTC)
    return metadata.model_copy(
        update={
            "title": choose_session_title(metadata, messages),
            "status": status,
            "updated_at": timestamp,
        },
    )


def _trim_optional(value: str | None) -> str | None:
    if value is None:
        return None
    return _trim_text(value, limit=PREVIEW_MAX_LENGTH)
