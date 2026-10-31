from datetime import UTC, datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, Field, TypeAdapter

from claude_code_py.common.ids import new_message_id

MessageKind = Literal["user", "assistant", "tool_use", "tool_result"]


def _now_utc() -> datetime:
    return datetime.now(UTC)


class BaseMessage(BaseModel):
    id: str = Field(default_factory=new_message_id)
    kind: MessageKind
    created_at: datetime = Field(default_factory=_now_utc)


class UserMessage(BaseMessage):
    kind: Literal["user"] = "user"
    content: str


class AssistantMessage(BaseMessage):
    kind: Literal["assistant"] = "assistant"
    content: str


class ToolUseMessage(BaseMessage):
    kind: Literal["tool_use"] = "tool_use"
    tool_name: str
    tool_use_id: str
    arguments: dict[str, object] = Field(default_factory=dict)


class ToolResultMessage(BaseMessage):
    kind: Literal["tool_result"] = "tool_result"
    tool_name: str
    tool_use_id: str
    output: str
    is_error: bool = False


Message: TypeAlias = Annotated[
    UserMessage | AssistantMessage | ToolUseMessage | ToolResultMessage,
    Field(discriminator="kind"),
]

MESSAGE_ADAPTER = TypeAdapter(Message)


def serialize_message(message: Message) -> dict[str, object]:
    return MESSAGE_ADAPTER.dump_python(message, mode="json")


def deserialize_message(data: dict[str, object]) -> Message:
    return MESSAGE_ADAPTER.validate_python(data)
