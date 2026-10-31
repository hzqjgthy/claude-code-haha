from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.tools._helpers import get_shared_state_bucket


def build_agents_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.strip().split()
        tasks = context.task_service.list_tasks()
        team_bucket = get_shared_state_bucket(context.tool_context, "team_state")
        teams = team_bucket.get("teams", {})
        active_team = team_bucket.get("active_team")
        plugin_agent_paths = [
            (plugin.name, path)
            for plugin in context.plugins
            for path in plugin.manifest.agents
        ]

        if args[:1] == ["show"] and len(args) > 1:
            task = context.task_service.get_task(args[1])
            if task is None:
                return CommandResult(
                    kind="error",
                    message=f"Unknown agent task '{args[1]}'.",
                )
            lines = [
                "Agent task:",
                f"task_id: {task.task_id}",
                f"status: {task.status}",
                f"kind: {task.kind}",
                f"background: {task.background}",
                f"model: {task.model}",
                f"owner: {task.owner or '(none)'}",
                f"description: {task.description}",
                f"prompt: {task.prompt}",
                f"result_text: {task.result_text or '(none)'}",
                f"error_message: {task.error_message or '(none)'}",
            ]
            if task.metadata:
                lines.append(f"metadata: {task.metadata}")
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:agents",
                dialog_title="Agents",
                dialog_lines=lines,
            )

        lines = [
            "Agents overview:",
            f"active_agent_tasks: {len(tasks)}",
            f"active_team: {active_team or '(none)'}",
            f"team_count: {len(teams) if isinstance(teams, dict) else 0}",
            f"plugin_agent_paths: {len(plugin_agent_paths)}",
        ]
        if tasks:
            lines.append("tasks:")
            for task in tasks[:10]:
                lines.append(
                    f"- {task.task_id[:8]} | {task.kind} | {task.status} | bg={task.background} | {task.description}",
                )
        else:
            lines.append("tasks: (none)")
        if active_team and isinstance(teams, dict) and isinstance(teams.get(active_team), dict):
            members = teams[active_team].get("members", [])
            lines.append(f"team members: {', '.join(members) or '(none)'}")
        if plugin_agent_paths:
            lines.append("plugin agent roots:")
            for plugin_name, path in plugin_agent_paths[:10]:
                lines.append(f"- {plugin_name}: {path}")
        else:
            lines.append("plugin agent roots: (none)")
        lines.append("Use /agents show <task_id> to inspect one delegated task.")
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:agents",
            dialog_title="Agents",
            dialog_lines=lines,
            selector_kind="selector:agents",
            selector_title="Active Agents",
            selector_options=[
                CommandSelectorOption(
                    label=f"{task.task_id[:8]} | {task.status}",
                    command=f"/agents show {task.task_id}",
                    description=f"{task.kind} | {task.description}",
                    preview_lines=[
                        f"kind={task.kind}",
                        f"background={task.background}",
                        f"model={task.model}",
                        f"owner={task.owner or '(none)'}",
                    ],
                )
                for task in tasks[:10]
            ]
            or None,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="agents",
            description="Inspect delegated agent tasks and plugin agent roots.",
            command_type="local_ui",
            argument_hint="[show <task_id>]",
        ),
        usage="/agents [show <task_id>]",
        handler=handler,
    )
