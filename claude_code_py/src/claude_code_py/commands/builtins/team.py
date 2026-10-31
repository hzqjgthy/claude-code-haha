from datetime import UTC, datetime

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.tools._helpers import get_shared_state_bucket


def build_team_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        bucket = get_shared_state_bucket(context.tool_context, "team_state")
        teams = bucket.setdefault("teams", {})
        active_team_name = bucket.get("active_team")
        active_team = teams.get(active_team_name) if active_team_name else None
        args = invocation.args.split(maxsplit=2)

        if not args or args[0] == "show":
            if not active_team_name or not isinstance(active_team, dict):
                return CommandResult(kind="message", message="No active team.")
            mailboxes = active_team.get("mailboxes", {})
            members = active_team.get("members", [])
            lines = [
                f"team_name: {active_team_name}",
                f"description: {active_team.get('description') or '(none)'}",
                f"lead_agent_id: {active_team.get('lead_agent_id')}",
                f"members: {', '.join(members) or '(none)'}",
                f"mailboxes: {len(mailboxes)}",
            ]
            for member in members:
                lines.append(f"member:{member} | mailbox={len(mailboxes.get(member, []))}")
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:team",
                dialog_title="Team",
                dialog_lines=lines,
                selector_kind="selector:team",
                selector_title="Team Members",
                selector_options=[
                    CommandSelectorOption(
                        label=member,
                        command=f"/team mailbox {member}",
                        description=f"{len(mailboxes.get(member, []))} message(s)",
                        preview_lines=[
                            f"member: {member}",
                            f"mailbox_count: {len(mailboxes.get(member, []))}",
                        ],
                    )
                    for member in members
                ]
                or None,
            )

        action = args[0].lower()
        if action == "create" and len(args) > 1:
            if active_team_name:
                return CommandResult(kind="error", message=f"Team '{active_team_name}' is already active.")
            team_name = args[1].strip()
            description = args[2].strip() if len(args) > 2 else None
            lead_agent_id = f"team-lead:{context.session_state.metadata.session_id}"
            teams[team_name] = {
                "team_name": team_name,
                "description": description,
                "lead_agent_id": lead_agent_id,
                "members": [lead_agent_id],
                "mailboxes": {lead_agent_id: []},
            }
            bucket["active_team"] = team_name
            return CommandResult(kind="message", message=f"Created team {team_name}.")

        if action == "delete":
            if not active_team_name:
                return CommandResult(kind="message", message="No active team to delete.")
            teams.pop(active_team_name, None)
            bucket["active_team"] = None
            return CommandResult(kind="message", message=f"Deleted team {active_team_name}.")

        if action == "spawn" and len(args) > 2:
            if not active_team_name or not isinstance(active_team, dict):
                return CommandResult(kind="error", message="Create a team first with /team create <name>.")
            teammate_name = args[1].strip()
            prompt = args[2].strip()
            members = active_team.setdefault("members", [])
            mailboxes = active_team.setdefault("mailboxes", {})
            if teammate_name not in members:
                members.append(teammate_name)
            mailboxes.setdefault(teammate_name, [])
            submission = context.task_service.submit_agent_task(
                description=f"teammate:{teammate_name}",
                prompt=prompt,
                history=list(context.session_state.messages),
                model=context.model_name,
                system_prompt=context.base_system_prompt,
                session_id=context.session_state.metadata.session_id,
                background=True,
                kind="teammate",
                owner=teammate_name,
                metadata={"team_name": active_team_name, "teammate_name": teammate_name},
            )
            return CommandResult(
                kind="message",
                message=(
                    f"Spawned teammate {teammate_name} in team {active_team_name}.\n"
                    f"task_id: {submission.task.task_id}"
                ),
            )

        if action == "stop" and len(args) > 1:
            if not active_team_name or not isinstance(active_team, dict):
                return CommandResult(kind="error", message="No active team.")
            teammate_name = args[1].strip()
            members = active_team.setdefault("members", [])
            if teammate_name not in members:
                return CommandResult(
                    kind="error",
                    message=f"Teammate '{teammate_name}' is not part of the active team.",
                )
            tasks = [
                task
                for task in context.task_service.list_tasks()
                if task.kind == "teammate"
                and task.owner == teammate_name
                and task.metadata.get("team_name") == active_team_name
                and task.status in {"pending", "running"}
            ]
            if not tasks:
                active_team["members"] = [member for member in members if member != teammate_name]
                active_team.setdefault("mailboxes", {}).pop(teammate_name, None)
                return CommandResult(
                    kind="message",
                    message=f"Stopped teammate {teammate_name}.",
                )
            stopped: list[str] = []
            for task in tasks:
                try:
                    context.task_service.cancel_task(task.task_id)
                    stopped.append(task.task_id)
                except RuntimeError:
                    continue
            if stopped:
                active_team["members"] = [member for member in members if member != teammate_name]
                active_team.setdefault("mailboxes", {}).pop(teammate_name, None)
            return CommandResult(
                kind="message",
                message=(
                    f"Stopped teammate {teammate_name}."
                    if stopped
                    else f"Could not stop teammate {teammate_name}."
                ),
            )

        if action == "message" and len(args) > 2:
            if not active_team_name or not isinstance(active_team, dict):
                return CommandResult(kind="error", message="Create a team first with /team create <name>.")
            target = args[1].strip()
            rendered = args[2].strip()
            mailboxes = active_team.setdefault("mailboxes", {})
            targets = (
                list(active_team.get("members", []))
                if target == "*"
                else [target]
            )
            record = {
                "from": context.session_state.metadata.session_id,
                "text": rendered,
                "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            }
            for member in targets:
                mailboxes.setdefault(member, []).append(record)
            return CommandResult(
                kind="message",
                message=(
                    f"Broadcast message to {len(targets)} member(s)."
                    if target == "*"
                    else f"Sent message to {target}."
                ),
            )

        if action == "mailbox" and len(args) > 1:
            if not active_team_name or not isinstance(active_team, dict):
                return CommandResult(kind="error", message="No active team.")
            member = args[1].strip()
            records = active_team.setdefault("mailboxes", {}).get(member, [])
            lines = [f"Mailbox: {member}"]
            if not records:
                lines.append("(empty)")
            else:
                for record in records[-20:]:
                    lines.append(
                        f"{record.get('timestamp')} | from={record.get('from')} | {record.get('text')}"
                    )
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:team-mailbox",
                dialog_title=f"Team Mailbox: {member}",
                dialog_lines=lines,
            )

        return CommandResult(
            kind="error",
            message=(
                "Usage: /team, /team create <name> [description], /team delete, "
                "/team spawn <member> <prompt>, /team stop <member>, "
                "/team message <member|*> <text>, or /team mailbox <member>"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="team",
            description="Manage an in-process team and teammate tasks.",
            command_type="local_ui",
            argument_hint="[show|create|delete|spawn|stop|message|mailbox ...]",
        ),
        usage="/team [show|create|delete|spawn|stop|message|mailbox ...]",
        handler=handler,
    )
