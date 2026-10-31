from typing import Literal

from pydantic import BaseModel

EventKind = Literal["info", "warning", "error"]


class AppEvent(BaseModel):
    kind: EventKind
    message: str
