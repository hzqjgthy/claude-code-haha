from claude_code_py.commands.builtins._helpers import bool_word
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_sandbox_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        tokens = invocation.args.strip().split()
        prefs = context.runtime_state_store.get_preferences()
        if not tokens or tokens == ["status"]:
            lines = [
                "Sandbox settings:",
                f"enabled: {bool_word(prefs.sandbox_enabled)}",
                f"auto_allow: {bool_word(prefs.sandbox_auto_allow)}",
                "allow_unsandboxed_fallback: "
                f"{bool_word(prefs.sandbox_allow_unsandboxed_fallback)}",
                (
                    "behavior: when enabled, Bash / PowerShell / WebFetch now "
                    "surface sandbox-aware approval reasons before falling back "
                    "to unsandboxed execution."
                ),
                (
                    "note: the Python refactor still does not have a real "
                    "sandbox executor yet, so these approvals currently guard "
                    "the fallback path rather than enforce isolation."
                ),
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:sandbox",
                dialog_title="Sandbox",
                dialog_lines=lines,
            )

        if tokens[0] in {"on", "off"}:
            enabled = tokens[0] == "on"
            context.runtime_state_store.update_preferences(sandbox_enabled=enabled)
            return CommandResult(
                kind="message",
                message=f"Sandbox preference updated: enabled={bool_word(enabled)}.",
            )

        if len(tokens) == 2 and tokens[0] in {"auto-allow", "fallback"}:
            enabled = _parse_on_off(tokens[1])
            if enabled is None:
                return CommandResult(
                    kind="error",
                    message=f"Usage: /sandbox {tokens[0]} <on|off>",
                )
            field_name = (
                "sandbox_auto_allow"
                if tokens[0] == "auto-allow"
                else "sandbox_allow_unsandboxed_fallback"
            )
            context.runtime_state_store.update_preferences(**{field_name: enabled})
            return CommandResult(
                kind="message",
                message=f"Sandbox preference updated: {tokens[0]}={bool_word(enabled)}.",
            )

        return CommandResult(
            kind="error",
            message=(
                "Usage: /sandbox [status|on|off|auto-allow <on|off>|fallback <on|off>]"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="sandbox",
            description="Inspect and update persisted sandbox preferences.",
            command_type="local_ui",
            argument_hint="[status|on|off|auto-allow <on|off>|fallback <on|off>]",
            aliases=["sandbox-toggle"],
        ),
        usage="/sandbox [status|on|off|auto-allow <on|off>|fallback <on|off>]",
        handler=handler,
    )


def _parse_on_off(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized == "on":
        return True
    if normalized == "off":
        return False
    return None
