from claude_code_py.commands.builtins._helpers import bool_word
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_ide_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.strip().split()
        prefs = context.runtime_state_store.get_preferences()
        ide_servers = [
            server.server_name
            for server in context.mcp_server_configs
            if "ide" in server.server_name.lower()
            or "vscode" in server.server_name.lower()
            or "jetbrains" in server.server_name.lower()
        ]

        if not args or args == ["status"]:
            lines = [
                "IDE integration:",
                f"auto_connect: {bool_word(prefs.ide_auto_connect)}",
                f"preferred_ide: {prefs.preferred_ide or '(none)'}",
                f"detected_ide_mcp_servers: {', '.join(ide_servers) or '(none)'}",
                "Use /ide auto-connect <on|off>, /ide prefer <server>, or /ide clear.",
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:ide",
                dialog_title="IDE",
                dialog_lines=lines,
                selector_kind="selector:ide",
                selector_title="IDE Preferences",
                selector_options=[
                    CommandSelectorOption(
                        label=f"Prefer {server}",
                        command=f"/ide prefer {server}",
                    )
                    for server in ide_servers
                ]
                + [
                    CommandSelectorOption(
                        label="Auto-connect on",
                        command="/ide auto-connect on",
                    ),
                    CommandSelectorOption(
                        label="Auto-connect off",
                        command="/ide auto-connect off",
                    ),
                    CommandSelectorOption(
                        label="Clear preference",
                        command="/ide clear",
                    ),
                ],
            )

        if len(args) == 2 and args[0] == "auto-connect":
            enabled = _parse_on_off(args[1])
            if enabled is None:
                return CommandResult(
                    kind="error",
                    message="Usage: /ide auto-connect <on|off>",
                )
            context.runtime_state_store.update_preferences(ide_auto_connect=enabled)
            return CommandResult(
                kind="message",
                message=f"IDE auto-connect updated to {bool_word(enabled)}.",
            )

        if len(args) >= 2 and args[0] == "prefer":
            value = " ".join(args[1:]).strip()
            context.runtime_state_store.update_preferences(preferred_ide=value)
            return CommandResult(
                kind="message",
                message=f"Preferred IDE updated to {value}.",
            )

        if args == ["clear"]:
            context.runtime_state_store.update_preferences(preferred_ide=None)
            return CommandResult(
                kind="message",
                message="Cleared the preferred IDE setting.",
            )

        if args == ["open"]:
            return CommandResult(
                kind="message",
                message=(
                    "Open-in-IDE routing is not implemented yet in claude-code-py. "
                    "This command already persists the IDE preference for later stages."
                ),
            )

        return CommandResult(
            kind="error",
            message="Usage: /ide [status|auto-connect <on|off>|prefer <server>|clear|open]",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="ide",
            description="Manage IDE preferences and show detected IDE MCP servers.",
            command_type="local_ui",
            argument_hint="[status|auto-connect <on|off>|prefer <server>|clear|open]",
        ),
        usage="/ide [status|auto-connect <on|off>|prefer <server>|clear|open]",
        handler=handler,
    )


def _parse_on_off(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized == "on":
        return True
    if normalized == "off":
        return False
    return None
