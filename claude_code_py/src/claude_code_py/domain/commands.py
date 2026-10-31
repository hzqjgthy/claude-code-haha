from typing import Literal

from pydantic import BaseModel, Field

CommandType = Literal["prompt", "local", "local_ui"]


class CommandSpec(BaseModel):
    name: str
    description: str
    command_type: CommandType
    argument_hint: str | None = None
    aliases: list[str] = Field(default_factory=list)
