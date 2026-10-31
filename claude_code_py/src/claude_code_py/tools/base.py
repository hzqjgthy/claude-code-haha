from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from claude_code_py.domain.permissions import (
    PermissionDecision,
    PermissionPromptRequest,
    PermissionTarget,
)
from claude_code_py.domain.tools import ToolExecutionResult, ToolSpec
from claude_code_py.providers.llm.base import LLMProvider
from claude_code_py.providers.shell.base import ShellProvider

InputModelT = TypeVar("InputModelT", bound=BaseModel)


class ToolExecutionError(RuntimeError):
    """Raised when a tool cannot complete successfully."""


@dataclass(slots=True)
class ToolContext:
    workspace_root: Path
    cwd: Path
    default_model: str
    llm_provider: LLMProvider | None = None
    shell_provider: ShellProvider | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def allowed_roots(self) -> list[Path]:
        roots = [self.workspace_root.resolve()]
        for value in self.metadata.get("additional_workspace_roots", []):
            try:
                roots.append(Path(str(value)).expanduser().resolve())
            except OSError:
                continue
        unique_roots: list[Path] = []
        for root in roots:
            if root not in unique_roots:
                unique_roots.append(root)
        return unique_roots

    def register_additional_root(self, raw_path: str) -> Path:
        root = Path(raw_path).expanduser().resolve()
        roots = [
            Path(str(value)).expanduser().resolve()
            for value in self.metadata.get("additional_workspace_roots", [])
        ]
        if root not in roots:
            roots.append(root)
            self.metadata["additional_workspace_roots"] = [str(item) for item in roots]
        return root

    def resolve_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = self.cwd / candidate
        resolved = candidate.resolve()
        allowed_roots = self.allowed_roots()
        for root in allowed_roots:
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue
        rendered_roots = ", ".join(str(root) for root in allowed_roots)
        raise ToolExecutionError(
            f"Path '{resolved}' is outside allowed roots: {rendered_roots}.",
        )
        return resolved

    def resolve_cwd(self, raw_path: str | None = None) -> Path:
        if raw_path is None:
            return self.resolve_path(str(self.cwd))
        return self.resolve_path(raw_path)


class BaseTool(ABC, Generic[InputModelT]):
    name: str
    description: str
    input_model: type[InputModelT]
    read_only: bool = False
    destructive: bool = False

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            read_only=self.read_only,
            destructive=self.destructive,
            input_schema=self.input_model.model_json_schema(),
        )

    def invoke(self, arguments: dict[str, object], context: ToolContext) -> ToolExecutionResult:
        payload = self.input_model.model_validate(arguments)
        self.validate(payload, context)
        decision = self.check_permissions(payload, context)
        if decision.behavior != "allow":
            reason = decision.reason or f"{self.name} permission denied."
            raise ToolExecutionError(reason)
        return self.execute(payload, context)

    def validate(self, payload: InputModelT, context: ToolContext) -> None:
        del payload, context

    def check_permissions(
        self,
        payload: InputModelT,
        context: ToolContext,
    ) -> PermissionDecision:
        del payload, context
        return PermissionDecision(behavior="allow")

    def permission_targets(
        self,
        payload: InputModelT,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        del payload, context
        return [PermissionTarget(tool_name=self.name)]

    def history_paths(
        self,
        payload: InputModelT,
        context: ToolContext,
    ) -> list[Path]:
        del payload, context
        return []

    def build_permission_request(
        self,
        payload: InputModelT,
        context: ToolContext,
        *,
        summary: str,
        reason: str | None,
    ) -> PermissionPromptRequest:
        return PermissionPromptRequest(
            tool_name=self.name,
            summary=summary,
            reason=reason,
            targets=self.permission_targets(payload, context),
        )

    def summarize(self, payload: InputModelT) -> str:
        return f"{self.name} invocation"

    @abstractmethod
    def execute(self, payload: InputModelT, context: ToolContext) -> ToolExecutionResult:
        raise NotImplementedError
