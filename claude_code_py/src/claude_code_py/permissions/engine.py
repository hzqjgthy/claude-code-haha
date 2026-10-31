from claude_code_py.domain.permissions import (
    PermissionContext,
    PermissionDecision,
    PermissionTarget,
)
from claude_code_py.permissions.decision import choose_stronger_rule, decision_from_rule
from claude_code_py.permissions.rules import match_rule


class PermissionEngine:
    def evaluate(self, context: PermissionContext, targets: list[PermissionTarget]) -> PermissionDecision:
        if context.mode == "bypass_permissions":
            return PermissionDecision(behavior="allow", reason="bypass_permissions mode")

        matched_rule = None
        for rule in context.rules:
            if any(match_rule(rule, target) for target in targets):
                matched_rule = choose_stronger_rule(matched_rule, rule)

        if matched_rule is not None:
            if matched_rule.behavior == "ask" and not context.ask_mode_enabled:
                return PermissionDecision(
                    behavior="deny",
                    reason="Permission requires approval, but interactive ask mode is unavailable.",
                    source=matched_rule.source,
                    matched_rule=matched_rule,
                )
            return decision_from_rule(matched_rule, self._reason_for_rule(matched_rule))

        return self._fallback_decision(context, targets)

    @staticmethod
    def _reason_for_rule(rule) -> str:
        if rule.kind and rule.pattern:
            return f"Matched {rule.source} rule: {rule.tool_name}({rule.kind}:{rule.pattern})"
        return f"Matched {rule.source} rule: {rule.tool_name}"

    @staticmethod
    def _fallback_decision(
        context: PermissionContext,
        targets: list[PermissionTarget],
    ) -> PermissionDecision:
        tool_name = targets[0].tool_name if targets else "tool"

        if context.mode == "accept_edits":
            if tool_name in {"Read", "Write", "Edit"}:
                return PermissionDecision(behavior="allow", reason="accept_edits mode")
            if context.ask_mode_enabled:
                return PermissionDecision(
                    behavior="ask",
                    reason=f"{tool_name} requires approval in accept_edits mode.",
                )
            return PermissionDecision(
                behavior="deny",
                reason=f"{tool_name} requires approval in accept_edits mode, but ask mode is unavailable.",
            )

        if context.mode == "plan":
            if tool_name == "Read":
                return PermissionDecision(behavior="allow", reason="plan mode allows reads")
            if context.ask_mode_enabled:
                return PermissionDecision(
                    behavior="ask",
                    reason=f"{tool_name} requires approval in plan mode.",
                )
            return PermissionDecision(
                behavior="deny",
                reason=f"{tool_name} requires approval in plan mode, but ask mode is unavailable.",
            )

        if context.ask_mode_enabled:
            return PermissionDecision(
                behavior="ask",
                reason=f"{tool_name} requires approval in default mode.",
            )

        return PermissionDecision(
            behavior="allow",
            reason="default mode without ask UI defaults to allow",
        )
