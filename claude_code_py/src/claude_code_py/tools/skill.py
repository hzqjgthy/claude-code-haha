from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.application.task_service import TaskSubmission
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.skills.loader import load_skills
from claude_code_py.tools._helpers import get_loaded_skills, get_task_service
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class SkillToolInput(BaseModel):
    skill_name: str
    arguments: str | None = None
    run_in_background: bool = False


class SkillTool(BaseTool[SkillToolInput]):
    name = "Skill"
    description = "Execute a loaded skill in an isolated agent run."
    input_model = SkillToolInput
    read_only = False
    destructive = False

    def validate(self, payload: SkillToolInput, context: ToolContext) -> None:
        if not payload.skill_name.strip():
            raise ToolExecutionError("skill_name cannot be empty.")

    def summarize(self, payload: SkillToolInput) -> str:
        return payload.skill_name

    def execute(self, payload: SkillToolInput, context: ToolContext) -> ToolExecutionResult:
        task_service = get_task_service(context)
        skills = get_loaded_skills(context)
        if not skills:
            skills = load_skills(context.workspace_root)
        target = next(
            (
                skill
                for skill in skills
                if skill.command_name == payload.skill_name
                or skill.name.lower() == payload.skill_name.lower()
            ),
            None,
        )
        if target is None:
            raise ToolExecutionError(f"Unknown skill '{payload.skill_name}'.")

        base_prompt = payload.arguments.strip() if payload.arguments else ""
        user_prompt = (
            base_prompt
            or f"Apply the '{target.name}' skill to the current task."
        )
        system_prompt = "\n\n".join(
            part
            for part in [
                str(context.metadata.get("system_prompt") or "").strip() or None,
                f"Skill name: {target.name}",
                f"Skill description: {target.description}" if target.description else None,
                f"When to use: {target.when_to_use}" if target.when_to_use else None,
                "Follow the skill instructions below:",
                target.content,
            ]
            if part
        )
        history = context.metadata.get("conversation_history", [])
        current_model = str(context.metadata.get("current_model", context.default_model))
        session_id = context.metadata.get("session_id")
        submission: TaskSubmission = task_service.submit_agent_task(
            description=f"Skill: {target.command_name}",
            prompt=user_prompt,
            history=history if isinstance(history, list) else [],
            model=current_model,
            system_prompt=system_prompt,
            session_id=session_id if isinstance(session_id, str) else None,
            background=payload.run_in_background,
            parent_task_id=(
                context.metadata.get("current_task_id")
                if isinstance(context.metadata.get("current_task_id"), str)
                else None
            ),
        )
        if payload.run_in_background:
            return ToolExecutionResult(
                tool_name=self.name,
                tool_use_id=None,
                output=(
                    f"Background skill task started.\n"
                    f"task_id: {submission.task.task_id}\n"
                    f"skill: {target.command_name}"
                ),
                structured_output=submission.task.model_dump(mode="json"),
            )
        if submission.result is None:
            raise ToolExecutionError("Skill execution did not return a result.")
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=submission.result.text,
            structured_output={
                "task": submission.task.model_dump(mode="json"),
                "result": submission.result.model_dump(mode="json"),
            },
        )
