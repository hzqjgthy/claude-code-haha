from datetime import datetime
from pathlib import Path

from claude_code_py.commands.builtins._session_exports import build_share_bundle
from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.common.json import to_json
from claude_code_py.domain.commands import CommandSpec


def build_share_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        if not context.session_state.messages:
            return CommandResult(
                kind="error",
                message="No conversation to share.",
            )

        target = invocation.args.strip()
        share_path = _resolve_share_path(context, target)
        share_path.parent.mkdir(parents=True, exist_ok=True)
        bundle = build_share_bundle(context)
        share_path.write_text(
            to_json(bundle, indent=2) + "\n",
            encoding="utf-8",
        )
        return CommandResult(
            kind="message",
            message=f"Share bundle written to: {share_path}",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="share",
            description="Create a portable local share bundle for the current session.",
            command_type="local_ui",
            argument_hint="[target.json]",
        ),
        usage="/share [target.json]",
        handler=handler,
    )


def _resolve_share_path(context: CommandContext, raw_target: str) -> Path:
    if raw_target:
        candidate = Path(raw_target).expanduser()
        if not candidate.is_absolute():
            candidate = context.tool_context.cwd / candidate
        if candidate.suffix.lower() != ".json":
            candidate = candidate.with_suffix(".json")
        return candidate.resolve()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_id = context.session_state.metadata.session_id
    return (
        context.container.paths.data_dir
        / "shares"
        / f"{session_id}-{timestamp}.json"
    ).resolve()
