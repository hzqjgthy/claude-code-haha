from pathlib import Path

from pydantic import BaseModel

from claude_code_py.app.container import AppContainer
from claude_code_py.domain.permissions import (
    PermissionBehavior,
    PermissionContext,
    PermissionDecision,
    PermissionDenialRecord,
    PermissionMode,
    PermissionRule,
    PermissionRuleSource,
    PermissionTarget,
    ShadowedPermissionRule,
)
from claude_code_py.permissions.engine import PermissionEngine
from claude_code_py.permissions.rules import (
    PermissionSettingsDocument,
    build_context,
    build_rules_from_document,
    detect_shadowed_rules,
    load_settings_document,
    parse_permission_rules,
    render_rule,
    write_settings_document,
)
from claude_code_py.tools.base import BaseTool, ToolContext

MAX_DENIAL_RECORDS = 50


class PermissionService:
    def __init__(
        self,
        *,
        context: PermissionContext,
        user_settings_path: Path | None = None,
        project_settings_path: Path | None = None,
        engine: PermissionEngine | None = None,
    ) -> None:
        self._context = context
        self._user_settings_path = user_settings_path
        self._project_settings_path = project_settings_path
        self._engine = engine or PermissionEngine()
        self._recent_denials: list[PermissionDenialRecord] = []

    @classmethod
    def from_sources(
        cls,
        *,
        container: AppContainer,
        workspace_root: Path,
        mode: str | PermissionMode = "default",
        ask_mode_enabled: bool = False,
        allow_rules: list[str] | None = None,
        deny_rules: list[str] | None = None,
        ask_rules: list[str] | None = None,
        session_rules: list[str] | None = None,
    ) -> "PermissionService":
        rules = []

        user_settings_path = (
            container.paths.data_dir / "settings" / "user_settings.json"
        )
        project_settings_path = workspace_root / ".claude_code_py" / "settings.json"

        user_doc = load_settings_document(user_settings_path)
        if user_doc is not None:
            rules.extend(build_rules_from_document(user_doc, source="user_settings"))
            if user_doc.permission_mode is not None:
                mode = user_doc.permission_mode  # type: ignore[assignment]

        project_doc = load_settings_document(project_settings_path)
        if project_doc is not None:
            rules.extend(
                build_rules_from_document(project_doc, source="project_settings")
            )
            if project_doc.permission_mode is not None:
                mode = project_doc.permission_mode  # type: ignore[assignment]

        if session_rules:
            rules.extend(
                parse_permission_rules(
                    session_rules, source="session", behavior="allow"
                )
            )

        if allow_rules:
            rules.extend(
                parse_permission_rules(allow_rules, source="cli_arg", behavior="allow")
            )
        if deny_rules:
            rules.extend(
                parse_permission_rules(deny_rules, source="cli_arg", behavior="deny")
            )
        if ask_rules:
            rules.extend(
                parse_permission_rules(ask_rules, source="cli_arg", behavior="ask")
            )

        context = build_context(
            mode=mode, ask_mode_enabled=ask_mode_enabled, rules=rules
        )
        return cls(
            context=context,
            user_settings_path=user_settings_path,
            project_settings_path=project_settings_path,
        )

    def evaluate(
        self,
        tool: BaseTool,
        payload: BaseModel,
        tool_context: ToolContext,
    ) -> PermissionDecision:
        targets = tool.permission_targets(payload, tool_context)
        return self._engine.evaluate(self._context, targets)

    def add_rules(self, rules: list[PermissionRule]) -> None:
        for candidate in rules:
            self._context.rules = [
                rule
                for rule in self._context.rules
                if not (
                    rule.source == candidate.source
                    and rule.tool_name == candidate.tool_name
                    and rule.kind == candidate.kind
                    and rule.pattern == candidate.pattern
                )
            ]
            self._context.rules.append(candidate)

    def list_rules(self) -> list[PermissionRule]:
        return [rule.model_copy(deep=True) for rule in self._context.rules]

    def clear_rules(self, *, source: str | None = None) -> int:
        original_count = len(self._context.rules)
        if source is None:
            self._context.rules = []
        else:
            self._context.rules = [
                rule for rule in self._context.rules if rule.source != source
            ]
        return original_count - len(self._context.rules)

    def current_mode(self) -> PermissionMode:
        return self._context.mode

    def set_mode(self, mode: PermissionMode) -> None:
        self._context.mode = mode

    def remember_targets(
        self,
        targets: list[PermissionTarget],
        *,
        behavior: PermissionBehavior,
        destination: PermissionRuleSource = "session",
    ) -> list[PermissionRule]:
        remembered = self._targets_to_rules(
            targets,
            behavior=behavior,
            source=destination,
        )
        self.add_rules(remembered)
        if destination == "project_settings":
            self._persist_rules(remembered, source=destination)
        return remembered

    def record_denial(
        self,
        *,
        tool_name: str,
        summary: str,
        reason: str,
        request_kind: str = "generic",
        targets: list[PermissionTarget] | None = None,
        source: PermissionRuleSource | None = None,
    ) -> None:
        self._recent_denials.append(
            PermissionDenialRecord(
                tool_name=tool_name,
                summary=summary,
                reason=reason,
                request_kind=request_kind,  # type: ignore[arg-type]
                targets=targets or [],
                source=source,
            )
        )
        self._recent_denials = self._recent_denials[-MAX_DENIAL_RECORDS:]

    def list_recent_denials(self) -> list[PermissionDenialRecord]:
        return [record.model_copy(deep=True) for record in reversed(self._recent_denials)]

    def detect_shadowed_rules(
        self,
        *,
        sandbox_auto_allow_enabled: bool = False,
    ) -> list[ShadowedPermissionRule]:
        return detect_shadowed_rules(
            self._context.rules,
            sandbox_auto_allow_enabled=sandbox_auto_allow_enabled,
        )

    @staticmethod
    def _targets_to_rules(
        targets: list[PermissionTarget],
        *,
        behavior: PermissionBehavior,
        source: PermissionRuleSource,
    ) -> list[PermissionRule]:
        if not targets:
            return []

        prioritized = PermissionService._prioritize_targets(targets)
        return [
            PermissionRule(
                source=source,
                behavior=behavior,
                tool_name=target.tool_name,
                kind=target.kind,
                pattern=target.value,
            )
            for target in prioritized
        ]

    def _persist_rules(
        self,
        rules: list[PermissionRule],
        *,
        source: PermissionRuleSource,
    ) -> None:
        if source != "project_settings" or self._project_settings_path is None:
            return

        document = (
            load_settings_document(self._project_settings_path)
            or PermissionSettingsDocument()
        )
        for rule in rules:
            rendered = render_rule(rule)
            bucket = getattr(document, rule.behavior)
            if rendered not in bucket:
                bucket.append(rendered)
        write_settings_document(self._project_settings_path, document)

    @staticmethod
    def _prioritize_targets(targets: list[PermissionTarget]) -> list[PermissionTarget]:
        specific_commands = [
            target
            for target in targets
            if target.kind == "command" and target.value is not None
        ]
        if specific_commands:
            return specific_commands

        specific_paths_or_domains = [
            target
            for target in targets
            if target.kind in {"path", "domain"} and target.value is not None
        ]
        if specific_paths_or_domains:
            return specific_paths_or_domains

        prefixes = [
            target
            for target in targets
            if target.kind == "command_prefix" and target.value is not None
        ]
        if prefixes:
            return prefixes

        return [targets[0]]
