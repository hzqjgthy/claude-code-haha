import json

from claude_code_py.commands.loader import (
    CommandDialogAction,
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.providers.mcp import McpHttpServerConfig, McpStdioServerConfig


def build_mcp_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.split(maxsplit=2)
        if not args or args[0] == "list":
            lines = _render_mcp_overview_lines(context)
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                selector_kind="selector:mcp",
                selector_title="MCP Servers",
                selector_options=_build_mcp_selector_options(context),
            )

        action = args[0].lower()
        if action == "tools":
            lines = _render_mcp_tools_lines(context)
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:mcp-tools",
                dialog_title="MCP Tools",
                dialog_lines=lines,
            )

        if action == "resources":
            return _list_resources(context, args[1] if len(args) > 1 else None)

        if action == "read" and len(args) > 2:
            return _read_resource(context, args[1], args[2])

        if action == "show" and len(args) > 1:
            return _show_server(context, args[1])

        if action == "reconnect":
            return _reconnect(context, args[1] if len(args) > 1 else None)

        if action == "auth" and len(args) > 1:
            return _auth_hint(context, args[1])

        if action == "registry":
            return _registry_snapshot(context)

        return CommandResult(
            kind="error",
            message=(
                "Usage: /mcp, /mcp tools, /mcp resources [server], /mcp read <server> <uri>, "
                "/mcp show <server_name>, /mcp reconnect [server_name], /mcp auth <server_name>, "
                "or /mcp registry"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="mcp",
            description="Inspect, reconnect, and manage loaded MCP servers.",
            command_type="local_ui",
            argument_hint="[tools|resources|read|show|reconnect|auth|registry]",
        ),
        usage="/mcp [tools|resources|read|show|reconnect|auth|registry]",
        handler=handler,
    )


def _render_mcp_overview_lines(context: CommandContext) -> list[str]:
    states = context.mcp_manager.server_states()
    if not states and not context.mcp_manager.errors:
        return [
            "No MCP servers loaded.",
            "Checked <workspace>/.mcp.json and --mcp-config values.",
        ]
    lines = ["MCP servers:"]
    for state in states:
        auth = "needs-auth" if state.auth_required else "ready"
        lines.append(
            f"{state.server_name} | source={state.source} | transport={state.transport} | "
            f"status={'connected' if state.connected else 'failed'} | auth={auth} | "
            f"tools={state.tool_count} | resources={state.resource_count}",
        )
        if state.last_error:
            lines.append(f"  error: {state.last_error}")
    for error in context.mcp_manager.errors:
        if error not in lines:
            lines.append(f"error: {error}")
    lines.append("Use /mcp show <server_name> to inspect one server.")
    return lines


def _render_mcp_tools_lines(context: CommandContext) -> list[str]:
    if not context.mcp_tool_definitions:
        if context.mcp_server_configs:
            return [
                "No MCP tools were discovered from the currently loaded servers."
            ]
        return ["No MCP servers loaded."]

    lines = ["MCP tools:"]
    for definition in sorted(
        context.mcp_tool_definitions,
        key=lambda item: (item.server_name, item.tool_name),
    ):
        lines.append(
            f"{definition.qualified_name} | server={definition.server_name} | "
            f"{definition.description or '(no description)'}",
        )
    return lines


def _list_resources(context: CommandContext, server_name: str | None) -> CommandResult:
    try:
        resources = context.mcp_manager.list_resources(server_name)
    except Exception as exc:
        return CommandResult(kind="error", message=str(exc))
    if not resources:
        return CommandResult(kind="message", message="No MCP resources found.")
    lines = ["MCP resources:"]
    for resource in resources:
        lines.append(
            f"{resource.server_name} | {resource.uri} | {resource.name or '(unnamed)'} | {resource.mime_type or '(unknown)'}"
        )
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:mcp-resources",
        dialog_title="MCP Resources",
        dialog_lines=lines,
    )


def _read_resource(context: CommandContext, server_name: str, uri: str) -> CommandResult:
    try:
        result = context.mcp_manager.read_resource(server_name, uri)
    except Exception as exc:
        return CommandResult(kind="error", message=str(exc))
    lines = [
        f"server: {server_name}",
        f"uri: {uri}",
        "",
        json.dumps(result, ensure_ascii=False, indent=2),
    ]
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:mcp-read-resource",
        dialog_title=f"MCP Resource: {server_name}",
        dialog_lines=lines,
    )


def _show_server(context: CommandContext, server_name: str) -> CommandResult:
    target = next(
        (server for server in context.mcp_server_configs if server.server_name == server_name),
        None,
    )
    if target is None:
        return CommandResult(
            kind="error",
            message=f"Unknown MCP server '{server_name}'.",
        )

    state = next(
        (item for item in context.mcp_manager.server_states() if item.server_name == server_name),
        None,
    )
    lines = [
        f"server_name: {target.server_name}",
        f"source: {target.source}",
        f"connected: {'yes' if state and state.connected else 'no'}",
        f"auth_required: {'yes' if state and state.auth_required else 'no'}",
        f"tool_count: {state.tool_count if state else 0}",
        f"resource_count: {state.resource_count if state else 0}",
    ]
    if isinstance(target.config, McpHttpServerConfig):
        lines.extend(
            [
                "transport: http",
                f"url: {target.config.url}",
                f"timeout_ms: {target.config.timeout_ms}",
                f"headers: {', '.join(sorted(target.config.headers)) or '(none)'}",
            ]
        )
    elif isinstance(target.config, McpStdioServerConfig):
        lines.extend(
            [
                "transport: stdio",
                f"command: {target.config.command}",
                f"args: {' '.join(target.config.args) or '(none)'}",
                f"cwd: {target.config.cwd or '(workspace root)'}",
            ]
        )
    if state and state.last_error:
        lines.extend(["", "last_error:", state.last_error])

    tools = [
        definition.tool_name
        for definition in context.mcp_tool_definitions
        if definition.server_name == target.server_name
    ]
    lines.append(f"tools: {', '.join(sorted(tools)) or '(none)'}")
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:mcp-show",
        dialog_title=f"MCP Server: {target.server_name}",
        dialog_lines=lines,
        dialog_actions=[
            CommandDialogAction(label="MCP Menu", command="/mcp"),
            CommandDialogAction(label="Show Tools", command="/mcp tools"),
            CommandDialogAction(label="Show Resources", command=f"/mcp resources {target.server_name}"),
            CommandDialogAction(label="Reconnect", command=f"/mcp reconnect {target.server_name}"),
        ],
    )


def _reconnect(context: CommandContext, server_name: str | None) -> CommandResult:
    try:
        names = context.mcp_manager.reconnect(server_name)
        refreshed = context.mcp_manager.list_tool_definitions()
    except Exception as exc:
        return CommandResult(kind="error", message=str(exc))
    context.mcp_tool_definitions = refreshed
    scope = ", ".join(names) if names else "(none)"
    return CommandResult(
        kind="message",
        message=f"Reconnected MCP server(s): {scope}",
    )


def _auth_hint(context: CommandContext, server_name: str) -> CommandResult:
    try:
        message = context.mcp_manager.auth_hint(server_name)
    except Exception as exc:
        return CommandResult(kind="error", message=str(exc))
    return CommandResult(kind="message", message=message)


def _registry_snapshot(context: CommandContext) -> CommandResult:
    states = context.mcp_manager.server_states()
    resources = context.mcp_manager.list_resources()
    lines = [
        "MCP registry snapshot:",
        f"servers: {len(states)}",
        f"tools: {len(context.mcp_tool_definitions)}",
        f"resources: {len(resources)}",
    ]
    for state in states:
        lines.append(
            f"{state.server_name} | transport={state.transport} | status={'connected' if state.connected else 'failed'} | auth={'needs-auth' if state.auth_required else 'ready'}"
        )
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:mcp-registry",
        dialog_title="MCP Registry",
        dialog_lines=lines,
    )


def _build_mcp_selector_options(context: CommandContext) -> list[CommandSelectorOption]:
    options: list[CommandSelectorOption] = []
    for state in context.mcp_manager.server_states():
        preview_lines = [
            f"source: {state.source}",
            f"transport: {state.transport}",
            f"status: {'connected' if state.connected else 'failed'}",
            f"auth_required: {'yes' if state.auth_required else 'no'}",
            f"tools: {state.tool_count}",
            f"resources: {state.resource_count}",
        ]
        if state.last_error:
            preview_lines.extend(["", "last_error:", state.last_error])
        options.append(
            CommandSelectorOption(
                label=state.server_name,
                command=f"/mcp show {state.server_name}",
                description=f"{state.transport} | {'connected' if state.connected else 'failed'}",
                preview_lines=preview_lines,
            )
        )
    options.extend(
        [
            CommandSelectorOption(
                label="All MCP Tools",
                command="/mcp tools",
                description=f"{len(context.mcp_tool_definitions)} discovered tool(s)",
                preview_lines=[
                    "List every MCP tool currently exposed by loaded servers.",
                ],
            ),
            CommandSelectorOption(
                label="All MCP Resources",
                command="/mcp resources",
                description="List readable MCP resources.",
                preview_lines=["Inspect resources across all configured MCP servers."],
            ),
            CommandSelectorOption(
                label="Registry Snapshot",
                command="/mcp registry",
                description="Show current server/tool/resource counts.",
                preview_lines=["Inspect the current MCP registry snapshot."],
            ),
        ]
    )
    return options
