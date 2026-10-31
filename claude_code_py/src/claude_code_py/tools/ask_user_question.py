from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from claude_code_py.domain.permissions import PermissionPromptRequest
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.tools.permission_preview import clip_text


class AskUserOption(BaseModel):
    label: str
    description: str


class AskUserQuestion(BaseModel):
    question: str
    header: str
    options: list[AskUserOption] = Field(min_length=2, max_length=4)
    multiSelect: bool = False


class AskUserQuestionToolInput(BaseModel):
    questions: list[AskUserQuestion] = Field(min_length=1, max_length=4)


class AskUserQuestionTool(BaseTool[AskUserQuestionToolInput]):
    name = "AskUserQuestion"
    description = "Ask the user one or more multiple-choice questions."
    input_model = AskUserQuestionToolInput
    read_only = True
    destructive = False

    def summarize(self, payload: AskUserQuestionToolInput) -> str:
        return payload.questions[0].header

    def build_permission_request(
        self,
        payload: AskUserQuestionToolInput,
        context: ToolContext,
        *,
        summary: str,
        reason: str | None,
    ) -> PermissionPromptRequest:
        del context
        lines: list[str] = []
        for index, question in enumerate(payload.questions, start=1):
            labels = ", ".join(option.label for option in question.options)
            lines.append(f"{index}. [{question.header}] {question.question}")
            lines.append(f"   options: {labels}")
        return PermissionPromptRequest(
            tool_name=self.name,
            summary=summary,
            reason=reason,
            request_kind="ask_user_question",
            title="Ask the user a question",
            subtitle=f"{len(payload.questions)} question(s)",
            prompt="Claude wants to ask you a structured question.",
            detail_lines=lines,
            preview=clip_text("\n".join(lines), max_lines=20, max_chars=2000),
            metadata={"question_count": len(payload.questions)},
        )

    def execute(self, payload: AskUserQuestionToolInput, context: ToolContext) -> ToolExecutionResult:
        callback = context.metadata.get("ask_user_callback")
        if not callable(callback):
            raise ToolExecutionError(
                "AskUserQuestion is unavailable in this runtime.",
            )
        answers = callback(payload.model_dump(mode="json"))
        if not isinstance(answers, dict):
            raise ToolExecutionError("AskUserQuestion callback returned an invalid response.")
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output="\n".join(
                f"{question} -> {answer}"
                for question, answer in answers.items()
            ),
            structured_output={
                "questions": payload.model_dump(mode="json")["questions"],
                "answers": answers,
            },
        )
