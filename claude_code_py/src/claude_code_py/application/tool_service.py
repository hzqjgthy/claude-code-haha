from collections.abc import Callable
from dataclasses import dataclass

from claude_code_py.application.file_history_service import FileHistoryService
from claude_code_py.application.permission_service import PermissionService
from claude_code_py.domain.messages import ToolResultMessage, ToolUseMessage
from claude_code_py.domain.permissions import (
    PermissionDecision,
    PermissionPromptChoice,
    PermissionPromptRequest,
)
from claude_code_py.domain.tools import (
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolSpec,
)
from claude_code_py.tools.base import ToolContext
from claude_code_py.tools.registry import ToolRegistry

PermissionPromptCallback = Callable[[PermissionPromptRequest], PermissionPromptChoice]


@dataclass(slots=True)
class ToolExecutionEnvelope:
    spec: ToolSpec
    summary: str
    use_message: ToolUseMessage
    result_message: ToolResultMessage
    result: ToolExecutionResult


class ToolService:
    def __init__(
        self,
        registry: ToolRegistry,
        *,
        permission_service: PermissionService | None = None,
    ) -> None:
        self._registry = registry
        self._permission_service = permission_service

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def list_specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self._registry.list_tools()]

    def execute(
        self,
        request: ToolExecutionRequest,
        context: ToolContext,
    ) -> ToolExecutionEnvelope:
        tool = self._registry.get(request.tool_name)
        tool_use_id = request.tool_use_id or f"tool-{request.tool_name.lower()}"
        try:
            payload = tool.input_model.model_validate(request.arguments)
            summary = tool.summarize(payload)
        except Exception:
            payload = None
            summary = tool.name
        use_message = ToolUseMessage(
            tool_name=request.tool_name,
            tool_use_id=tool_use_id,
            arguments=request.arguments,
        )
        try:
            if payload is None:
                payload = tool.input_model.model_validate(request.arguments)
            tool.validate(payload, context)
            decision = self._evaluate_permission(tool, payload, context)
            decision = self._resolve_permission_request(
                tool,
                payload,
                context,
                summary=summary,
                decision=decision,
            )
            if decision.behavior != "allow":
                reason = decision.reason or f"{tool.name} permission denied."
                raise PermissionError(reason)
            self._capture_file_history(tool, payload, context)
            result = tool.execute(payload, context)
        except Exception as exc:
            result = ToolExecutionResult(
                tool_name=request.tool_name,
                tool_use_id=tool_use_id,
                output=str(exc),
                is_error=True,
                structured_output=self._exception_metadata(exc),
            )
        if result.tool_use_id is None:
            result.tool_use_id = tool_use_id
        result_message = ToolResultMessage(
            tool_name=result.tool_name,
            tool_use_id=result.tool_use_id,
            output=result.output,
            is_error=result.is_error,
        )
        return ToolExecutionEnvelope(
            spec=tool.spec(),
            summary=summary,
            use_message=use_message,
            result_message=result_message,
            result=result,
        )

    def _evaluate_permission(
        self,
        tool,
        payload,
        context: ToolContext,
    ) -> PermissionDecision:
        base_decision = (
            self._permission_service.evaluate(tool, payload, context)
            if self._permission_service is not None
            else PermissionDecision(behavior="allow")
        )
        if base_decision.behavior != "allow":
            return base_decision
        return tool.check_permissions(payload, context)

    def _resolve_permission_request(
        self,
        tool,
        payload,
        context: ToolContext,
        *,
        summary: str,
        decision: PermissionDecision,
    ) -> PermissionDecision:
        if decision.behavior != "ask":
            if decision.behavior == "deny" and self._permission_service is not None:
                self._permission_service.record_denial(
                    tool_name=tool.name,
                    summary=summary,
                    reason=decision.reason or f"{tool.name} denied.",
                    targets=tool.permission_targets(payload, context),
                    source=decision.source,
                )
            return decision

        callback = context.metadata.get("permission_prompt_callback")
        if not callable(callback):
            denied = PermissionDecision(
                behavior="deny",
                reason=decision.reason or f"{tool.name} requires approval.",
            )
            if self._permission_service is not None:
                self._permission_service.record_denial(
                    tool_name=tool.name,
                    summary=summary,
                    reason=denied.reason or f"{tool.name} requires approval.",
                    targets=tool.permission_targets(payload, context),
                    source=decision.source,
                )
            return denied

        request = tool.build_permission_request(
            payload,
            context,
            summary=summary,
            reason=decision.reason,
        )
        targets = request.targets
        choice = callback(request)

        if choice == "allow_once":
            return PermissionDecision(
                behavior="allow",
                reason=f"{tool.name} approved for this request.",
            )

        if choice == "allow_session":
            if self._permission_service is not None:
                self._permission_service.remember_targets(targets, behavior="allow")
            return PermissionDecision(
                behavior="allow",
                reason=f"{tool.name} approved for this session.",
            )

        if choice == "allow_project":
            if self._permission_service is not None:
                self._permission_service.remember_targets(
                    targets,
                    behavior="allow",
                    destination="project_settings",
                )
            return PermissionDecision(
                behavior="allow",
                reason=f"{tool.name} approved for this project.",
            )

        if choice == "deny_session":
            if self._permission_service is not None:
                self._permission_service.remember_targets(targets, behavior="deny")
                self._permission_service.record_denial(
                    tool_name=tool.name,
                    summary=summary,
                    reason=f"{tool.name} denied for this session.",
                    request_kind=request.request_kind,
                    targets=targets,
                    source="session",
                )
            return PermissionDecision(
                behavior="deny",
                reason=f"{tool.name} denied for this session.",
            )

        if choice == "deny_project":
            if self._permission_service is not None:
                self._permission_service.remember_targets(
                    targets,
                    behavior="deny",
                    destination="project_settings",
                )
                self._permission_service.record_denial(
                    tool_name=tool.name,
                    summary=summary,
                    reason=f"{tool.name} denied for this project.",
                    request_kind=request.request_kind,
                    targets=targets,
                    source="project_settings",
                )
            return PermissionDecision(
                behavior="deny",
                reason=f"{tool.name} denied for this project.",
            )

        denied = PermissionDecision(
            behavior="deny",
            reason=decision.reason or f"{tool.name} denied by user.",
        )
        if self._permission_service is not None:
            self._permission_service.record_denial(
                tool_name=tool.name,
                summary=summary,
                reason=denied.reason or f"{tool.name} denied by user.",
                request_kind=request.request_kind,
                targets=targets,
                source=decision.source,
            )
        return denied

    def _capture_file_history(self, tool, payload, context: ToolContext) -> None:
        turn_id = context.metadata.get("current_turn_id")
        session_id = context.metadata.get("session_id")
        if not isinstance(turn_id, str) or not isinstance(session_id, str):
            return
        history_paths = tool.history_paths(payload, context)
        if not history_paths:
            return
        app_container = context.metadata.get("app_container")
        if app_container is None or not hasattr(app_container, "paths"):
            return
        service = FileHistoryService(app_container.paths.data_dir / "file_history")
        for path in history_paths:
            try:
                service.capture_before_mutation(
                    session_id=session_id,
                    turn_id=turn_id,
                    file_path=path,
                )
            except Exception:
                continue

    @staticmethod
    def _exception_metadata(exc: Exception) -> dict[str, object]:
        metadata: dict[str, object] = {"exception_type": type(exc).__name__}
        if isinstance(exc, PermissionError):
            metadata["permission_error"] = True
        return metadata
