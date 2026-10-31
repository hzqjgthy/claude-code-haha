import json
from pathlib import Path

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_hooks_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        del invocation
        config_summaries = _discover_hook_configs(context.workspace_root)
        plugin_hooks = [
            (plugin.name, plugin.manifest.hooks)
            for plugin in context.plugins
            if plugin.manifest.hooks
        ]

        lines = [
            "Hooks snapshot:",
            "execution_support: not implemented yet",
        ]

        if config_summaries:
            lines.extend(["", "config files:"])
            for path, summary in config_summaries:
                lines.append(f"{path} | {summary}")
        else:
            lines.extend(["", "config files:", "(none discovered)"])

        if plugin_hooks:
            lines.extend(["", "plugin hooks:"])
            for plugin_name, hooks in plugin_hooks:
                lines.append(f"{plugin_name}: {', '.join(hooks)}")
        else:
            lines.extend(["", "plugin hooks:", "(none declared)"])

        lines.extend(
            [
                "",
                "This command currently inspects hook configuration only.",
            ]
        )
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:hooks",
            dialog_title="Hooks",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="hooks",
            description="Inspect discovered hook configuration and plugin hook declarations.",
            command_type="local_ui",
        ),
        usage="/hooks",
        handler=handler,
    )


def _discover_hook_configs(workspace_root: Path) -> list[tuple[Path, str]]:
    candidates = [
        Path.home() / ".claude" / "settings.json",
        workspace_root / ".claude" / "settings.json",
    ]
    summaries: list[tuple[Path, str]] = []
    for path in candidates:
        if not path.exists():
            continue
        summary = _summarize_hook_config(path)
        if summary is None:
            continue
        summaries.append((path, summary))
    return summaries


def _summarize_hook_config(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"invalid json: {exc}"
    if not isinstance(payload, dict):
        return "invalid settings root"
    hooks = payload.get("hooks")
    if hooks is None:
        return None
    if not isinstance(hooks, dict):
        return "hooks key exists but is not an object"
    event_names = sorted(str(key) for key in hooks)
    return f"events={len(event_names)} | {', '.join(event_names) or '(none)'}"
