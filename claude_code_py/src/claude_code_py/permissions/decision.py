from claude_code_py.domain.permissions import (
    PermissionDecision,
    PermissionRule,
    PermissionRuleSource,
)

SOURCE_PRIORITY: dict[PermissionRuleSource, int] = {
    "cli_arg": 0,
    "session": 1,
    "project_settings": 2,
    "user_settings": 3,
}

BEHAVIOR_PRIORITY = {
    "deny": 0,
    "ask": 1,
    "allow": 2,
}


def choose_stronger_rule(
    current: PermissionRule | None, candidate: PermissionRule
) -> PermissionRule:
    if current is None:
        return candidate

    # Session approvals/denials should override ask-rules so "approve for this
    # session" and "deny for this session" actually stick inside interactive UIs.
    if current.source == "session" and candidate.behavior == "ask":
        return current
    if candidate.source == "session" and current.behavior == "ask":
        return candidate

    current_key = (BEHAVIOR_PRIORITY[current.behavior], SOURCE_PRIORITY[current.source])
    candidate_key = (
        BEHAVIOR_PRIORITY[candidate.behavior],
        SOURCE_PRIORITY[candidate.source],
    )
    if candidate_key < current_key:
        return candidate
    return current


def decision_from_rule(
    rule: PermissionRule, reason: str | None = None
) -> PermissionDecision:
    return PermissionDecision(
        behavior=rule.behavior,
        reason=reason,
        source=rule.source,
        matched_rule=rule,
    )
