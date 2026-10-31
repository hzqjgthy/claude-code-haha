from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_shared_state_bucket
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class SendMessageToolInput(BaseModel):
    to: str
    summary: str | None = None
    message: str | dict[str, object]


class SendMessageTool(BaseTool[SendMessageToolInput]):
    name = "SendMessage"
    description = "Send a message to a teammate or team mailbox."
    input_model = SendMessageToolInput
    read_only = False
    destructive = False

    def summarize(self, payload: SendMessageToolInput) -> str:
        return payload.to

    def execute(self, payload: SendMessageToolInput, context: ToolContext) -> ToolExecutionResult:
        bucket = get_shared_state_bucket(context, "team_state")
        active_team = bucket.get("active_team")
        if not active_team:
            raise ToolExecutionError("No active team exists. Create one with TeamCreate first.")
        teams = bucket.setdefault("teams", {})
        team = teams.get(active_team)
        if not isinstance(team, dict):
            raise ToolExecutionError(f"Team '{active_team}' was not found.")
        mailbox_targets = (
            [member for member in team.get("members", [])]
            if payload.to == "*"
            else [payload.to]
        )
        rendered_message = (
            payload.message
            if isinstance(payload.message, str)
            else json.dumps(payload.message, ensure_ascii=False)
        )
        record = {
            "from": str(context.metadata.get("session_id", "main")),
            "summary": payload.summary,
            "text": rendered_message,
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        mailboxes = team.setdefault("mailboxes", {})
        for target in mailbox_targets:
            mailboxes.setdefault(target, []).append(record)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=(
                f"Message sent to {payload.to}."
                if payload.to != "*"
                else f"Message broadcast to {len(mailbox_targets)} recipient(s)."
            ),
            structured_output={
                "success": True,
                "recipients": mailbox_targets,
                "record": record,
            },
        )
