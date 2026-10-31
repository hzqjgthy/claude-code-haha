from typing import Any, Literal

from pydantic import BaseModel, Field

ToolDecision = Literal["allow", "ask", "deny"]


class ToolSpec(BaseModel):
    name: str
    description: str
    read_only: bool = False
    destructive: bool = False
    input_schema: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionRequest(BaseModel):
    tool_name: str
    tool_use_id: str | None = None
    arguments: dict[str, object] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    tool_name: str
    tool_use_id: str | None = None
    output: str
    is_error: bool = False
    structured_output: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    tool_use_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
