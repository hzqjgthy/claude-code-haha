from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_shared_state_bucket
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class TeamCreateToolInput(BaseModel):
    team_name: str
    description: str | None = None
    agent_type: str | None = None


class TeamCreateTool(BaseTool[TeamCreateToolInput]):
    name = "TeamCreate"
    description = "Create an in-memory team for multi-agent coordination."
    input_model = TeamCreateToolInput
    read_only = False
    destructive = False

    def validate(self, payload: TeamCreateToolInput, context: ToolContext) -> None:
        del context
        if not payload.team_name.strip():
            raise ToolExecutionError("team_name cannot be empty.")

    def summarize(self, payload: TeamCreateToolInput) -> str:
        return payload.team_name

    def execute(self, payload: TeamCreateToolInput, context: ToolContext) -> ToolExecutionResult:
        bucket = get_shared_state_bucket(context, "team_state")
        if bucket.get("active_team"):
            raise ToolExecutionError(
                f"Already leading team '{bucket['active_team']}'. Delete it first.",
            )
        lead_agent_id = f"team-lead-{uuid4().hex[:8]}"
        team = {
            "team_name": payload.team_name,
            "description": payload.description,
            "agent_type": payload.agent_type or "team-lead",
            "lead_agent_id": lead_agent_id,
            "members": [lead_agent_id],
            "mailboxes": {},
        }
        teams = bucket.setdefault("teams", {})
        teams[payload.team_name] = team
        bucket["active_team"] = payload.team_name
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=f"Created team {payload.team_name}.",
            structured_output=team,
        )
