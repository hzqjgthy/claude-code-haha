from __future__ import annotations

import time

from pydantic import BaseModel, Field

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext


class SleepToolInput(BaseModel):
    duration_ms: int = Field(ge=0, le=300_000)


class SleepTool(BaseTool[SleepToolInput]):
    name = "Sleep"
    description = "Wait for a specified duration."
    input_model = SleepToolInput
    read_only = True
    destructive = False

    def summarize(self, payload: SleepToolInput) -> str:
        return f"{payload.duration_ms}ms"

    def execute(self, payload: SleepToolInput, context: ToolContext) -> ToolExecutionResult:
        del context
        time.sleep(payload.duration_ms / 1000)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=f"Slept for {payload.duration_ms} ms.",
            structured_output={"duration_ms": payload.duration_ms},
        )
