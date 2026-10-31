import fnmatch
import json
from pathlib import Path
import re

from pydantic import BaseModel, Field

from claude_code_py.domain.permissions import (
    PermissionBehavior,
    PermissionContext,
    PermissionRule,
    PermissionRuleSource,
    PermissionTarget,
    ShadowedPermissionRule,
    normalize_permission_mode,
)

RULE_PATTERN = re.compile(
    r"^(?P<tool>[A-Za-z][A-Za-z0-9_]*)(?:\((?P<kind>[a-z_]+):(?P<value>.+)\))?$",
)


class PermissionSettingsDocument(BaseModel):
    permission_mode: str | None = None
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    ask: list[str] = Field(default_factory=list)


def parse_permission_rule(
    rule_text: str,
    *,
    source: PermissionRuleSource,
    behavior: PermissionBehavior,
) -> PermissionRule:
    normalized = rule_text.strip()
    if not normalized:
        raise ValueError("Permission rule cannot be empty.")

    match = RULE_PATTERN.match(normalized)
    if match is None:
        raise ValueError(f"Invalid permission rule: {rule_text}")

    kind = match.group("kind")
    if kind is not None and kind not in {"path", "domain", "command_prefix", "command"}:
        raise ValueError(f"Unsupported permission matcher kind: {kind}")

    return PermissionRule(
        source=source,
        behavior=behavior,
        tool_name=match.group("tool"),
        kind=kind,
        pattern=match.group("value"),
    )


def parse_permission_rules(
    values: list[str],
    *,
    source: PermissionRuleSource,
    behavior: PermissionBehavior,
) -> list[PermissionRule]:
    return [
        parse_permission_rule(rule_text, source=source, behavior=behavior)
        for rule_text in values
    ]


def load_settings_document(path: Path) -> PermissionSettingsDocument | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid permission settings file: {path}")
    return PermissionSettingsDocument.model_validate(raw)


def build_rules_from_document(
    document: PermissionSettingsDocument,
    *,
    source: PermissionRuleSource,
) -> list[PermissionRule]:
    return [
        *parse_permission_rules(document.allow, source=source, behavior="allow"),
        *parse_permission_rules(document.deny, source=source, behavior="deny"),
        *parse_permission_rules(document.ask, source=source, behavior="ask"),
    ]


def write_settings_document(
    path: Path,
    document: PermissionSettingsDocument,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def render_rule(rule: PermissionRule) -> str:
    if rule.kind is None or rule.pattern is None:
        return rule.tool_name
    return f"{rule.tool_name}({rule.kind}:{rule.pattern})"


def match_rule(rule: PermissionRule, target: PermissionTarget) -> bool:
    if rule.tool_name != target.tool_name:
        return False
    if rule.kind is None:
        return True
    if rule.kind != target.kind:
        return False
    if rule.pattern is None or target.value is None:
        return False
    return fnmatch.fnmatch(target.value, rule.pattern)


def detect_shadowed_rules(
    rules: list[PermissionRule],
    *,
    sandbox_auto_allow_enabled: bool = False,
) -> list[ShadowedPermissionRule]:
    unreachable: list[ShadowedPermissionRule] = []
    allow_rules = [rule for rule in rules if rule.behavior == "allow"]
    ask_rules = [rule for rule in rules if rule.behavior == "ask"]
    deny_rules = [rule for rule in rules if rule.behavior == "deny"]

    for allow_rule in allow_rules:
        if allow_rule.kind is None or allow_rule.pattern is None:
            continue

        deny_shadow = _find_tool_wide_rule(deny_rules, allow_rule.tool_name)
        if deny_shadow is not None:
            unreachable.append(
                ShadowedPermissionRule(
                    rule=allow_rule,
                    shadowed_by=deny_shadow,
                    shadow_type="deny",
                    reason=(
                        f"Blocked by tool-wide deny rule "
                        f"{render_rule(deny_shadow)} from {deny_shadow.source}."
                    ),
                    fix=(
                        f"Remove {render_rule(deny_shadow)} or remove the more "
                        f"specific allow rule {render_rule(allow_rule)}."
                    ),
                )
            )
            continue

        ask_shadow = _find_tool_wide_rule(ask_rules, allow_rule.tool_name)
        if ask_shadow is None:
            continue
        if (
            sandbox_auto_allow_enabled
            and allow_rule.tool_name == "Bash"
            and ask_shadow.source != "project_settings"
        ):
            continue
        unreachable.append(
            ShadowedPermissionRule(
                rule=allow_rule,
                shadowed_by=ask_shadow,
                shadow_type="ask",
                reason=(
                    f"Shadowed by tool-wide ask rule "
                    f"{render_rule(ask_shadow)} from {ask_shadow.source}."
                ),
                fix=(
                    f"Remove {render_rule(ask_shadow)} or remove the more "
                    f"specific allow rule {render_rule(allow_rule)}."
                ),
            )
        )
    return unreachable


def _find_tool_wide_rule(
    rules: list[PermissionRule],
    tool_name: str,
) -> PermissionRule | None:
    for rule in rules:
        if rule.tool_name == tool_name and rule.kind is None:
            return rule
    return None


def build_context(
    *,
    mode: str,
    ask_mode_enabled: bool,
    rules: list[PermissionRule],
) -> PermissionContext:
    return PermissionContext(
        mode=normalize_permission_mode(mode),
        ask_mode_enabled=ask_mode_enabled,
        rules=rules,
    )
