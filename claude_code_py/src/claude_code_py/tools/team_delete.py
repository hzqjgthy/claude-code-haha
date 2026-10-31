from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_shared_state_bucket
from claude_code_py.tools.base import BaseTool, ToolContext


class TeamDeleteToolInput(BaseModel):
    pass


class TeamDeleteTool(BaseTool[TeamDeleteToolInput]):
    name = "TeamDelete"
    description = "Delete the active in-memory team."
    input_model = TeamDeleteToolInput
    read_only = False
    destructive = True

    def execute(self, payload: TeamDeleteToolInput, context: ToolContext) -> ToolExecutionResult:
        del payload
        bucket = get_shared_state_bucket(context, "team_state")
        active_team = bucket.get("active_team")
        if not active_team:
            return ToolExecutionResult(
                tool_name=self.name,
                tool_use_id=None,
                output="No active team to delete.",
                structured_output={"success": True, "team_name": None},
            )
        teams = bucket.setdefault("teams", {})
        teams.pop(active_team, None)
        bucket["active_team"] = None
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=f"Deleted team {active_team}.",
            structured_output={"success": True, "team_name": active_team},
        )
