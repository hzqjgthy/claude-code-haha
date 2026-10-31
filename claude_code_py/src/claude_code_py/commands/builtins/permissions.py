from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.domain.permissions import PermissionRule, normalize_permission_mode
from claude_code_py.permissions.rules import parse_permission_rule, render_rule


def build_permissions_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.strip()
        if not args or args == "list":
            lines = _render_permissions_lines(context)
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:permissions",
                dialog_title="Permissions",
                dialog_lines=lines,
            )

        parts = args.split(maxsplit=1)
        action = parts[0].lower()
        remainder = parts[1].strip() if len(parts) > 1 else ""

        if action == "mode":
            if not remainder:
                return CommandResult(
                    kind="error",
                    message="Usage: /permissions mode <default|accept_edits|bypass_permissions|plan>",
                )
            try:
                next_mode = normalize_permission_mode(remainder)
            except ValueError as exc:
                return CommandResult(kind="error", message=str(exc))
            context.permission_service.set_mode(next_mode)
            context.permission_mode = context.permission_service.current_mode()
            context.bind_status()
            return CommandResult(
                kind="message",
                message=f"Permission mode updated to {context.permission_mode}.",
            )

        if action == "clear-session":
            removed = context.permission_service.clear_rules(source="session")
            return CommandResult(
                kind="message",
                message=f"Removed {removed} session rule(s).",
            )

        if action in {"allow", "deny", "ask"}:
            if not remainder:
                return CommandResult(
                    kind="error",
                    message=f"Usage: /permissions {action} <rule>",
                )
            try:
                rule = parse_permission_rule(
                    remainder,
                    source="session",
                    behavior=action,
                )
            except ValueError as exc:
                return CommandResult(kind="error", message=str(exc))
            context.permission_service.add_rules([rule])
            return CommandResult(
                kind="message",
                message=f"Added session {action} rule: {_render_rule(rule)}",
            )

        return CommandResult(
            kind="error",
            message=(
                "Usage: /permissions, /permissions mode <mode>, "
                "/permissions allow|deny|ask <rule>, or /permissions clear-session"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="permissions",
            description="Inspect and update runtime permission rules.",
            command_type="local_ui",
            argument_hint="[mode <mode>|allow <rule>|deny <rule>|ask <rule>|clear-session]",
            aliases=["allowed-tools"],
        ),
        usage="/permissions [mode <mode>|allow <rule>|deny <rule>|ask <rule>|clear-session]",
        handler=handler,
    )


def _render_permissions_lines(context: CommandContext) -> list[str]:
    prefs = context.runtime_state_store.get_preferences()
    rules = sorted(
        context.permission_service.list_rules(),
        key=lambda rule: (rule.behavior, rule.source, rule.tool_name, rule.kind or "", rule.pattern or ""),
    )
    shadowed = context.permission_service.detect_shadowed_rules(
        sandbox_auto_allow_enabled=prefs.sandbox_auto_allow,
    )
    recent_denials = context.permission_service.list_recent_denials()[:10]
    lines = [
        "Permissions:",
        f"mode: {context.permission_mode}",
        f"rule_count: {len(rules)}",
        f"shadowed_rule_count: {len(shadowed)}",
        f"recent_denials: {len(recent_denials)}",
    ]
    if not rules:
        lines.append("rules: (none)")
    else:
        for rule in rules:
            lines.append(
                f"{rule.behavior} | source={rule.source} | {_render_rule(rule)}",
            )
    if shadowed:
        lines.append("")
        lines.append("Shadowed rules:")
        for item in shadowed:
            lines.append(
                f"{_render_rule(item.rule)} | {item.shadow_type} by {_render_rule(item.shadowed_by)} | {item.reason}"
            )
    if recent_denials:
        lines.append("")
        lines.append("Recent denials:")
        for denial in recent_denials:
            lines.append(
                f"{denial.tool_name} | {denial.summary} | {denial.reason}"
            )
    lines.append("Use /permissions mode <mode> or /permissions allow|deny|ask <rule>.")
    lines.append("Interactive approval now supports once, session, and project persistence.")
    return lines


def _render_rule(rule: PermissionRule) -> str:
    return render_rule(rule)
