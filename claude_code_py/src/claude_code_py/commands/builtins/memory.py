from pathlib import Path

from claude_code_py.application.session_memory_service import SessionMemoryService
from claude_code_py.commands.loader import (
    CommandDialogAction,
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_memory_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        targets = _memory_targets(context)
        args = invocation.args.split(maxsplit=2)
        if not args:
            lines = _render_memory_list_lines(context, targets)
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                selector_kind="selector:memory",
                selector_title="Select Memory File",
                selector_options=[
                    _build_memory_selector_option(context, target)
                    for target in targets
                ],
            )

        action = args[0].lower()
        if action == "extract":
            if len(args) < 2:
                return CommandResult(
                    kind="error",
                    message="Usage: /memory extract <target> [instructions]",
                )
            target = _resolve_target(targets, args[1])
            if target is None:
                return CommandResult(
                    kind="error",
                    message=f"Unknown memory target '{args[1]}'.",
                )
            if target.key != "session":
                return CommandResult(
                    kind="error",
                    message="Only /memory extract session is supported right now.",
                )
            instructions = args[2].strip() if len(args) > 2 else ""
            service = _session_memory_service(context)
            path, content = service.update_from_session(
                context.session_state,
                workspace_root=context.workspace_root,
                tool_context=context.tool_context,
                model_name=context.model_name,
                instructions=instructions,
            )
            lines = [
                f"Extracted session memory to: {path}",
                "",
                *_read_memory_preview(path, max_lines=12),
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:memory-extract",
                dialog_title="Session Memory Extract",
                dialog_lines=lines,
                dialog_actions=[
                    CommandDialogAction(label="Show", command="/memory show session"),
                    CommandDialogAction(label="Edit", command="/memory edit session"),
                ],
            )

        if action in {"show", "path", "init", "edit"}:
            if len(args) < 2:
                return CommandResult(
                    kind="error",
                    message=f"Usage: /memory {action} <target>",
                )
            target = _resolve_target(targets, args[1])
            if target is None:
                return CommandResult(
                    kind="error",
                    message=f"Unknown memory target '{args[1]}'.",
                )
            if action == "path":
                return CommandResult(
                    kind="message",
                    message=f"{target.label}: {target.path}",
                )
            if action == "init":
                target.path.parent.mkdir(parents=True, exist_ok=True)
                if not target.path.exists():
                    target.path.write_text("", encoding="utf-8")
                return CommandResult(
                    kind="message",
                    message=f"Initialized memory file at {target.path}",
                )
            if action == "edit":
                existing_text = (
                    target.path.read_text(encoding="utf-8")
                    if target.path.exists()
                    else ""
                )
                return CommandResult(
                    kind="message",
                    message=f"Opening memory editor for {target.label}: {target.path}",
                    editor_kind="memory-editor",
                    editor_title=f"Edit Memory: {target.label}",
                    editor_path=str(target.path.resolve()),
                    editor_text=existing_text,
                    editor_language="markdown",
                )
            if not target.path.exists():
                return CommandResult(
                    kind="error",
                    message=f"Memory file does not exist: {target.path}",
                )
            content = target.path.read_text(encoding="utf-8").strip()
            if not content:
                content = "(empty)"
            return CommandResult(
                kind="message",
                message="\n".join(
                    [
                        f"{target.label}: {target.path}",
                        "",
                        content,
                    ]
                ),
                dialog_kind="command:memory-show",
                dialog_title=f"Memory: {target.label}",
                dialog_lines=[
                    f"{target.label}: {target.path}",
                    "",
                    content,
                ],
                dialog_actions=[
                    CommandDialogAction(label="Memory Menu", command="/memory"),
                    CommandDialogAction(
                        label="Edit",
                        command=f"/memory edit {target.key}",
                    ),
                ],
            )

        return CommandResult(
            kind="error",
            message=(
                "Usage: /memory, /memory show <target>, /memory edit <target>, "
                "/memory path <target>, /memory init <target>, or "
                "/memory extract session [instructions]"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="memory",
            description="Inspect project, local, and session memory files.",
            command_type="local_ui",
            argument_hint="[show|edit|path|init|extract <target>]",
        ),
        usage="/memory [show|edit|path|init|extract <target>]",
        handler=handler,
    )


class _MemoryTarget:
    def __init__(self, key: str, label: str, path: Path) -> None:
        self.key = key
        self.label = label
        self.path = path


def _memory_targets(context: CommandContext) -> list[_MemoryTarget]:
    session_id = context.session_state.metadata.session_id
    return [
        _MemoryTarget("user", "User memory", Path.home() / ".claude" / "CLAUDE.md"),
        _MemoryTarget("project", "Project memory", context.workspace_root / "CLAUDE.md"),
        _MemoryTarget(
            "project-dot",
            "Project .claude memory",
            context.workspace_root / ".claude" / "CLAUDE.md",
        ),
        _MemoryTarget(
            "local",
            "Local project memory",
            context.workspace_root / "CLAUDE.local.md",
        ),
        _MemoryTarget(
            "session",
            "Session memory",
            _session_memory_service(context).memory_path(session_id),
        ),
    ]


def _resolve_target(targets: list[_MemoryTarget], raw_key: str) -> _MemoryTarget | None:
    normalized = raw_key.strip().lower()
    for target in targets:
        if target.key == normalized:
            return target
    return None


def _render_memory_list_lines(
    context: CommandContext,
    targets: list[_MemoryTarget],
) -> list[str]:
    lines = ["Memory files:"]
    for target in targets:
        exists = "yes" if target.path.exists() else "no"
        lines.append(f"{target.key} | exists={exists} | {target.path}")

    rules_dir = context.workspace_root / ".claude" / "rules"
    if rules_dir.exists():
        rule_files = sorted(path.name for path in rules_dir.glob("*.md") if path.is_file())
        lines.append(f"rules | count={len(rule_files)} | {rules_dir}")
        for rule_file in rule_files[:10]:
            lines.append(f"  - {rule_file}")
    else:
        lines.append(f"rules | count=0 | {rules_dir}")

    lines.append("Use /memory show <target> or /memory extract session.")
    return lines


def _build_memory_selector_option(
    context: CommandContext,
    target: _MemoryTarget,
) -> CommandSelectorOption:
    exists = target.path.exists()
    preview_lines = [
        f"path: {target.path}",
        f"exists: {'yes' if exists else 'no'}",
    ]
    preview = _read_memory_preview(target.path)
    if preview:
        preview_lines.extend(["", *preview])
    elif target.key == "session":
        preview_lines.extend(
            [
                "",
                "Session memory is not extracted yet.",
                "Run /memory extract session to generate it from the current transcript.",
            ]
        )
    else:
        preview_lines.extend(
            [
                "",
                "This memory file does not exist yet.",
                "Selecting it opens the inline editor and saving will create it.",
            ]
        )
    command = (
        "/memory extract session"
        if target.key == "session" and not exists
        else f"/memory edit {target.key}"
    )
    return CommandSelectorOption(
        label=f"{target.label} ({target.key})",
        command=command,
        description=(
            "Extract memory from the current session."
            if target.key == "session" and not exists
            else (
                "Edit existing memory file."
                if exists
                else "Create and edit this memory file."
            )
        ),
        preview_lines=preview_lines,
    )


def _read_memory_preview(
    path: Path,
    *,
    max_lines: int = 6,
) -> list[str]:
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return [f"preview_error: {exc}"]
    if not content:
        return ["(empty file)"]
    preview_lines = ["preview:"]
    lines = content.splitlines()
    for line in lines[:max_lines]:
        preview_lines.append(_truncate_preview_line(line))
    if len(lines) > max_lines:
        preview_lines.append(f"... {len(lines) - max_lines} more line(s)")
    return preview_lines


def _truncate_preview_line(line: str, *, limit: int = 120) -> str:
    if len(line) <= limit:
        return line
    return f"{line[: limit - 3]}..."


def _session_memory_service(context: CommandContext) -> SessionMemoryService:
    return SessionMemoryService(
        context.container.paths.data_dir / "session_memory"
    )
