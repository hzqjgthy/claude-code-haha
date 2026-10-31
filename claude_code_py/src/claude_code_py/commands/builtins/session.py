from pathlib import Path

from claude_code_py.application.file_history_service import FileHistoryService
from claude_code_py.application.remote_hydration import load_hydrated_remote_bundle
from claude_code_py.application.session_memory_service import SessionMemoryService
from claude_code_py.commands.loader import (
    CommandDialogAction,
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.domain.messages import (
    AssistantMessage,
    ToolResultMessage,
    ToolUseMessage,
    UserMessage,
)


def build_session_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        args = invocation.args.strip().split()
        session_id = context.session_state.metadata.session_id

        if args and args[0].lower() == "background":
            return _handle_background(context, session_id, args[1:])

        if args and args[0].lower() == "connect":
            return _handle_connect(context, session_id, args[1:])

        if args and args[0].lower() == "send":
            return _handle_send(context, args[1:])

        if args and args[0].lower() == "wait":
            return _handle_wait(context, args[1:])

        if args and args[0].lower() in {"interrupt", "cancel"}:
            return _handle_interrupt(context)

        if args and args[0].lower() in {"events", "transcript"}:
            return _handle_events(context)

        if args and args[0].lower() in {"requests", "permissions"}:
            return _handle_requests(context)

        if args and args[0].lower() == "approve" and len(args) > 1:
            return _handle_permission_response(context, args[1], choice="allow_once")

        if args and args[0].lower() == "deny" and len(args) > 1:
            return _handle_permission_response(context, args[1], choice="deny_once")

        if args and args[0].lower() == "disconnect":
            if context.remote_session_manager is not None:
                context.remote_session_manager.disconnect_transport()
            status = context.remote_provider.disconnect(detail="Disconnected by user")
            return CommandResult(
                kind="message",
                message=f"Remote session disconnected: {status.mode}",
            )

        if args and args[0].lower() == "reconnect":
            if context.remote_session_manager is not None:
                context.remote_session_manager.reconnect_transport()
            status = context.remote_provider.reconnect()
            return CommandResult(
                kind="message",
                message=(
                    f"Remote session reconnected: {status.mode}"
                    if status.mode != "local"
                    else "No remote session is available to reconnect."
                ),
            )

        if args and args[0].lower() == "heartbeat":
            status = context.remote_provider.heartbeat()
            return CommandResult(
                kind="message",
                message=(
                    "Remote heartbeat recorded."
                    if status.mode != "local"
                    else "No remote session is active."
                ),
            )

        if args and args[0].lower() == "archive":
            if context.remote_session_manager is not None:
                context.remote_session_manager.disconnect_transport()
            archived = context.remote_provider.archive()
            if archived is None:
                return CommandResult(
                    kind="message",
                    message="No remote session is active, nothing to archive.",
                )
            return CommandResult(
                kind="message",
                message=(
                    f"Archived remote session {archived.remote_session_id or '(unknown)'} "
                    f"for local session {archived.local_session_id or '(unknown)'}."
                ),
            )

        if args and args[0].lower() in {"history", "archives"}:
            return _render_archives(context)

        if args and args[0].lower() == "hydrate" and len(args) > 1:
            return _hydrate_remote_bundle(context, session_id, args[1])

        return _render_session_status(context, session_id)

    return SlashCommand(
        spec=CommandSpec(
            name="session",
            description="Inspect the current session and manage remote lifecycle.",
            command_type="local_ui",
            aliases=["remote"],
            argument_hint="[background|connect|send|wait|interrupt|events|requests|approve|deny|disconnect|reconnect|heartbeat|archive|history|hydrate ...]",
        ),
        usage=(
            "/session [background [status|on|off]|connect <direct|bridge|ssh> ...|send <prompt>|"
            "wait [timeout]|interrupt|events|requests|approve <id>|deny <id>|disconnect|reconnect|heartbeat|archive|history|hydrate <bundle.json>]"
        ),
        handler=handler,
    )


def _handle_background(context: CommandContext, session_id: str, args: list[str]) -> CommandResult:
    if not args or args[0].lower() == "status":
        state = context.runtime_state_store.is_session_backgrounded(session_id)
        return CommandResult(
            kind="message",
            message=f"Session backgrounded: {'yes' if state else 'no'}",
        )
    if args[0].lower() in {"on", "off"}:
        enabled = args[0].lower() == "on"
        context.runtime_state_store.set_session_backgrounded(
            session_id,
            enabled,
        )
        return CommandResult(
            kind="message",
            message=f"Session backgrounding updated: {'on' if enabled else 'off'}.",
        )
    return CommandResult(
        kind="error",
        message="Usage: /session background [status|on|off]",
    )


def _handle_connect(context: CommandContext, session_id: str, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(
            kind="error",
            message="Usage: /session connect <direct|bridge|ssh> ...",
        )
    mode = args[0].lower()
    if mode == "direct":
        if len(args) < 2:
            return CommandResult(
                kind="error",
                message="Usage: /session connect direct <session_url> [remote_session_id]",
            )
        remote_session_id = args[2] if len(args) > 2 else f"remote-{session_id}"
        try:
            if context.remote_session_manager is not None:
                actual_transport = context.remote_session_manager.connect(
                    remote_session_id=remote_session_id,
                    local_session_id=session_id,
                    transport_mode="websocket",
                    session_url=args[1],
                )
            else:
                actual_transport = "websocket"
        except Exception as exc:
            return CommandResult(kind="error", message=str(exc))
        detail = (
            "Direct connect session"
            if actual_transport == "websocket"
            else "Direct connect session (local subprocess fallback)"
        )
        status = context.remote_provider.connect_direct(
            session_url=args[1],
            local_session_id=session_id,
            remote_session_id=remote_session_id,
            transport="websocket" if actual_transport == "websocket" else "subprocess",
            detail=detail,
        )
        return CommandResult(
            kind="message",
            message=(
                f"Connected direct remote session: {status.session_url}"
                if actual_transport == "websocket"
                else (
                    f"Connected direct remote session: {status.session_url}\n"
                    "transport: subprocess fallback"
                )
            ),
        )
    if mode == "bridge":
        if len(args) < 2:
            return CommandResult(
                kind="error",
                message="Usage: /session connect bridge <session_url> [remote_session_id]",
            )
        remote_session_id = args[2] if len(args) > 2 else f"bridge-{session_id}"
        status = context.remote_provider.connect_bridge(
            session_url=args[1],
            local_session_id=session_id,
            remote_session_id=remote_session_id,
        )
        if context.remote_session_manager is not None:
            context.remote_session_manager.connect(
                remote_session_id=remote_session_id,
                local_session_id=session_id,
                transport_mode="in_process",
            )
        return CommandResult(
            kind="message",
            message=f"Connected bridge session: {status.session_url}",
        )
    if mode == "ssh":
        if len(args) < 2:
            return CommandResult(
                kind="error",
                message="Usage: /session connect ssh <host> [remote_cwd]",
            )
        if context.remote_session_manager is not None:
            remote_session_id = f"ssh-{args[1]}-{session_id}"
            try:
                context.remote_session_manager.connect(
                    remote_session_id=remote_session_id,
                    local_session_id=session_id,
                    transport_mode="ssh",
                    ssh_host=args[1],
                    ssh_remote_cwd=args[2] if len(args) > 2 else None,
                )
            except Exception as exc:
                return CommandResult(kind="error", message=str(exc))
        else:
            remote_session_id = f"ssh-{args[1]}-{session_id}"
        status = context.remote_provider.connect_ssh(
            host=args[1],
            local_session_id=session_id,
            remote_cwd=args[2] if len(args) > 2 else None,
            remote_session_id=remote_session_id,
        )
        return CommandResult(
            kind="message",
            message=f"Connected SSH remote session: {status.session_url}",
        )
    return CommandResult(
        kind="error",
        message="Usage: /session connect <direct|bridge|ssh> ...",
    )


def _handle_send(context: CommandContext, args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(
            kind="error",
            message="Usage: /session send <prompt>",
        )
    if context.remote_session_manager is None:
        return CommandResult(kind="error", message="Remote session manager is unavailable.")
    try:
        task = context.remote_session_manager.submit_prompt(" ".join(args).strip())
    except Exception as exc:
        return CommandResult(kind="error", message=str(exc))
    return CommandResult(
        kind="message",
        message=f"Queued remote prompt as task {task.task_id}.",
    )


def _handle_wait(context: CommandContext, args: list[str]) -> CommandResult:
    timeout = 10.0
    if args:
        try:
            timeout = float(args[0])
        except ValueError:
            return CommandResult(
                kind="error",
                message="Usage: /session wait [timeout_seconds]",
            )
    if context.remote_session_manager is None:
        return CommandResult(kind="error", message="Remote session manager is unavailable.")
    task = context.remote_session_manager.wait(timeout=timeout)
    if task is None:
        return CommandResult(kind="message", message="No remote task has been queued.")
    lines = [
        f"task_id: {task.task_id}",
        f"status: {task.status}",
        f"result: {task.result_text or '(pending)'}",
        f"error: {task.error_message or '(none)'}",
    ]
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:session-wait",
        dialog_title="Remote Wait",
        dialog_lines=lines,
    )


def _handle_interrupt(context: CommandContext) -> CommandResult:
    if context.remote_session_manager is None:
        return CommandResult(kind="error", message="Remote session manager is unavailable.")
    interrupted = context.remote_session_manager.interrupt()
    if not interrupted:
        return CommandResult(kind="message", message="No active remote task is running.")
    return CommandResult(kind="message", message="Interrupted the active remote task.")


def _handle_events(context: CommandContext) -> CommandResult:
    if context.remote_session_manager is None:
        return CommandResult(kind="error", message="Remote session manager is unavailable.")
    messages = context.remote_session_manager.messages()
    events = context.remote_session_manager.events()
    if not messages and not events:
        return CommandResult(kind="message", message="No remote transcript messages.")
    lines = ["Remote events:"]
    lines.extend(events[-20:] or ["(none)"])
    lines.append("")
    lines.append("Remote transcript:")
    for message in messages[-20:]:
        if isinstance(message, UserMessage):
            lines.append(f"user: {message.content}")
        elif isinstance(message, AssistantMessage):
            lines.append(f"assistant: {message.content}")
        elif isinstance(message, ToolUseMessage):
            lines.append(f"tool_use:{message.tool_name} {message.arguments}")
        elif isinstance(message, ToolResultMessage):
            label = "tool_error" if message.is_error else "tool_result"
            lines.append(f"{label}:{message.tool_name} {message.output}")
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:session-events",
        dialog_title="Remote Transcript",
        dialog_lines=lines,
    )


def _handle_requests(context: CommandContext) -> CommandResult:
    if context.remote_session_manager is None:
        return CommandResult(kind="error", message="Remote session manager is unavailable.")
    requests = context.remote_session_manager.pending_permission_requests()
    if not requests:
        return CommandResult(kind="message", message="No pending remote permission requests.")
    lines = ["Pending remote permission requests:"]
    for item in requests:
        lines.extend(
            [
                f"{item.request_id} | {item.prompt.tool_name} | {item.prompt.summary}",
                f"  reason: {item.prompt.reason or '(none)'}",
            ]
        )
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:session-requests",
        dialog_title="Remote Permission Requests",
        dialog_lines=lines,
        dialog_actions=[
            CommandDialogAction(
                label="Approve First",
                command=f"/session approve {requests[0].request_id}",
            ),
            CommandDialogAction(
                label="Deny First",
                command=f"/session deny {requests[0].request_id}",
            ),
        ],
    )


def _handle_permission_response(context: CommandContext, request_id: str, *, choice) -> CommandResult:
    if context.remote_session_manager is None:
        return CommandResult(kind="error", message="Remote session manager is unavailable.")
    resolved = context.remote_session_manager.resolve_permission_request(request_id, choice)
    if not resolved:
        return CommandResult(
            kind="error",
            message=f"Unknown remote permission request '{request_id}'.",
        )
    return CommandResult(
        kind="message",
        message=(
            f"Approved remote permission request {request_id}."
            if choice == "allow_once"
            else f"Denied remote permission request {request_id}."
        ),
    )


def _hydrate_remote_bundle(
    context: CommandContext,
    session_id: str,
    raw_path: str,
) -> CommandResult:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (context.workspace_root / candidate).resolve()
    if not candidate.exists():
        return CommandResult(kind="error", message=f"Remote bundle not found: {candidate}")

    bundle = load_hydrated_remote_bundle(candidate)
    context.session_state = context.session_service.rewrite_messages(
        context.session_state,
        bundle.messages,
    )
    if bundle.title:
        context.session_state = context.session_service.rename_session(
            context.session_state,
            bundle.title,
        )
    context.remote_provider.hydrate(
        local_session_id=session_id,
        remote_session_id=bundle.remote_session_id,
        session_url=bundle.session_url,
        hydrated_from=str(bundle.source_path),
        detail="Hydrated remote transcript bundle",
    )
    hydrated_remote_session_id = bundle.remote_session_id or f"hydrated-{session_id}"
    if context.remote_session_manager is not None:
        remote_state = context.session_service.load_or_create(hydrated_remote_session_id)
        context.session_service.rewrite_messages(remote_state, bundle.messages)
        context.remote_session_manager.connect(
            remote_session_id=hydrated_remote_session_id,
            local_session_id=session_id,
            transport_mode="in_process",
        )
    context.bind_status()
    return CommandResult(
        kind="message",
        message=(
            f"Hydrated remote transcript from {bundle.source_path}.\n"
            f"messages: {len(bundle.messages)}\n"
            f"remote_session_id: {bundle.remote_session_id or '(none)'}"
        ),
        refresh_transcript=True,
    )


def _render_archives(context: CommandContext) -> CommandResult:
    archived = context.remote_provider.archived_sessions()
    if not archived:
        return CommandResult(kind="message", message="No archived remote sessions.")
    lines = ["Archived remote sessions:"]
    for item in archived[:20]:
        lines.append(
            f"{item.mode} | remote={item.remote_session_id or '(none)'} | "
            f"local={item.local_session_id or '(none)'} | "
            f"archived_at={item.archived_at.isoformat(timespec='seconds')} | "
            f"{item.session_url or '(no url)'}"
        )
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:session-history",
        dialog_title="Remote Session History",
        dialog_lines=lines,
    )


def _render_session_status(context: CommandContext, session_id: str) -> CommandResult:
    remote = context.remote_provider.status() if context.remote_provider else None
    remote_task = (
        context.remote_session_manager.current_task()
        if context.remote_session_manager is not None
        else None
    )
    pending_request_count = (
        len(context.remote_session_manager.pending_permission_requests())
        if context.remote_session_manager is not None
        else 0
    )
    transcript_path = (
        context.container.paths.sessions_dir
        / f"{context.session_state.metadata.session_id}.jsonl"
    )
    session_tag = context.runtime_state_store.get_session_tag(session_id)
    session_color = context.runtime_state_store.get_session_color(session_id)
    backgrounded = context.runtime_state_store.is_session_backgrounded(session_id)
    session_memory_path = SessionMemoryService(
        context.container.paths.data_dir / "session_memory"
    ).memory_path(session_id)
    file_history_count = FileHistoryService(
        context.container.paths.data_dir / "file_history"
    ).snapshot_count(session_id)
    archive_count = len(context.remote_provider.archived_sessions())

    if remote is None or remote.mode == "local":
        lines = [
            "Not in remote mode.",
            f"current_session_id: {context.session_state.metadata.session_id}",
            f"title: {context.session_state.metadata.title}",
            f"tag: {session_tag or '(none)'}",
            f"color: {session_color or 'default'}",
            f"backgrounded: {'yes' if backgrounded else 'no'}",
            f"transcript_path: {transcript_path}",
            f"session_memory_path: {session_memory_path}",
            f"file_history_snapshots: {file_history_count}",
            "remote_mode: local",
            f"remote_archive_count: {archive_count}",
            f"remote_pending_requests: {pending_request_count}",
            "remote_session_url: (none)",
            "Commands: /session connect direct|bridge|ssh ..., /session history, "
            "/session send <prompt>, /session requests, /session hydrate <bundle.json>",
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:session",
            dialog_title="Session",
            dialog_lines=lines,
        )

    lines = [
        "Remote session:",
        f"current_session_id: {context.session_state.metadata.session_id}",
        f"title: {context.session_state.metadata.title}",
        f"tag: {session_tag or '(none)'}",
        f"color: {session_color or 'default'}",
        f"backgrounded: {'yes' if backgrounded else 'no'}",
        f"session_memory_path: {session_memory_path}",
        f"file_history_snapshots: {file_history_count}",
        f"remote_mode: {remote.mode}",
        f"remote_connected: {'yes' if remote.connected else 'no'}",
        f"remote_transport: {remote.transport}",
        f"remote_session_id: {remote.remote_session_id or '(none)'}",
        f"remote_session_url: {remote.session_url or '(none)'}",
        f"remote_detail: {remote.detail or '(none)'}",
        f"remote_can_reconnect: {'yes' if remote.can_reconnect else 'no'}",
        f"remote_connected_at: {remote.connected_at.isoformat(timespec='seconds') if remote.connected_at else '(none)'}",
        f"remote_last_heartbeat: {remote.last_heartbeat_at.isoformat(timespec='seconds') if remote.last_heartbeat_at else '(none)'}",
        f"remote_hydrated_from: {remote.hydrated_from or '(none)'}",
        f"remote_archive_count: {archive_count}",
        f"remote_pending_requests: {pending_request_count}",
        f"remote_task_status: {remote_task.status if remote_task is not None else '(idle)'}",
    ]
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:session",
        dialog_title="Session",
        dialog_lines=lines,
        dialog_actions=[
            CommandDialogAction(label="Heartbeat", command="/session heartbeat"),
            CommandDialogAction(label="Reconnect", command="/session reconnect"),
            CommandDialogAction(label="Archive", command="/session archive"),
            CommandDialogAction(label="History", command="/session history"),
        ],
    )
