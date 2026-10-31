from claude_code_py.commands.loader import (
    CommandDialogAction,
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_tasks_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        tokens = invocation.args.split(maxsplit=3)
        if not tokens:
            tasks = context.task_service.list_tasks()
            if not tasks:
                return CommandResult(kind="message", message="No tasks found.")
            lines = ["Tasks:"]
            for task in tasks:
                lines.append(
                    f"{task.task_id} | {task.kind} | {task.status} | bg={task.background} | {task.description}",
                )
            lines.append("Use /tasks show <task_id>, /tasks output <task_id>, or /tasks stop <task_id>.")
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:tasks",
                dialog_title="Tasks",
                dialog_lines=lines,
                selector_kind="selector:tasks",
                selector_title="Tasks",
                selector_options=[
                    CommandSelectorOption(
                        label=f"{task.task_id[:8]} | {task.kind} | {task.status}",
                        command=f"/tasks show {task.task_id}",
                        description=task.description,
                        preview_lines=_task_preview_lines(task),
                    )
                    for task in tasks[:20]
                ],
            )

        action = tokens[0].lower()
        if action == "show" and len(tokens) > 1:
            task = context.task_service.get_task(tokens[1])
            if task is None:
                return CommandResult(
                    kind="error",
                    message=f"Unknown task '{tokens[1]}'.",
                )
            lines = _task_detail_lines(task)
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:task-show",
                dialog_title=f"Task: {task.task_id}",
                dialog_lines=lines,
                dialog_actions=[
                    CommandDialogAction(label="Output", command=f"/tasks output {task.task_id}"),
                    CommandDialogAction(label="Stop", command=f"/tasks stop {task.task_id}"),
                ],
            )

        if action == "output" and len(tokens) > 1:
            task = context.task_service.get_task(tokens[1])
            if task is None:
                return CommandResult(kind="error", message=f"Unknown task '{tokens[1]}'.")
            lines = [
                f"task_id: {task.task_id}",
                f"kind: {task.kind}",
                f"status: {task.status}",
                "",
                task.result_text or task.error_message or "(no output yet)",
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:task-output",
                dialog_title=f"Task Output: {task.task_id}",
                dialog_lines=lines,
            )

        if action == "stop" and len(tokens) > 1:
            try:
                task = context.task_service.cancel_task(tokens[1])
            except RuntimeError as exc:
                return CommandResult(kind="error", message=str(exc))
            return CommandResult(
                kind="message",
                message=f"Stopped task {task.task_id}.",
            )

        if action == "update" and len(tokens) > 3:
            task_id = tokens[1]
            field_name = tokens[2].lower()
            value = tokens[3].strip()
            allowed_fields = {"description", "prompt", "model", "owner", "status"}
            if field_name not in allowed_fields:
                return CommandResult(
                    kind="error",
                    message=f"Unsupported task field '{field_name}'.",
                )
            try:
                task = context.task_service.update_task(task_id, **{field_name: value})
            except RuntimeError as exc:
                return CommandResult(kind="error", message=str(exc))
            return CommandResult(
                kind="message",
                message=f"Updated task {task.task_id}: {field_name}={value}",
            )

        return CommandResult(
            kind="error",
            message=(
                "Usage: /tasks, /tasks show <task_id>, /tasks output <task_id>, "
                "/tasks stop <task_id>, or /tasks update <task_id> <field> <value>"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="tasks",
            description="List, inspect, stop, and update background tasks.",
            command_type="local_ui",
            argument_hint="[show|output|stop|update <task_id> ...]",
            aliases=["bashes"],
        ),
        usage="/tasks [show|output|stop|update <task_id> ...]",
        handler=handler,
    )


def _task_detail_lines(task) -> list[str]:
    lines = [
        f"task_id: {task.task_id}",
        f"kind: {task.kind}",
        f"status: {task.status}",
        f"background: {task.background}",
        f"model: {task.model}",
        f"owner: {task.owner or '(none)'}",
        f"session_id: {task.session_id}",
        f"parent_task_id: {task.parent_task_id or '(none)'}",
        f"description: {task.description}",
        f"prompt: {task.prompt}",
    ]
    if task.metadata:
        lines.extend(["", "metadata:"])
        for key, value in sorted(task.metadata.items()):
            lines.append(f"{key}: {value}")
    if task.result_text:
        lines.extend(["", "result:", task.result_text])
    if task.error_message:
        lines.extend(["", "error:", task.error_message])
    return lines


def _task_preview_lines(task) -> list[str]:
    lines = [
        f"kind: {task.kind}",
        f"status: {task.status}",
        f"background: {task.background}",
        f"owner: {task.owner or '(none)'}",
    ]
    if task.metadata:
        lines.extend(["", "metadata:"])
        for key, value in sorted(task.metadata.items()):
            lines.append(f"{key}: {value}")
    return lines
