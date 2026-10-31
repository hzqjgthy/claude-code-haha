from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_tag_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        requested = _normalize_tag(invocation.args)
        session_id = context.session_state.metadata.session_id
        current_tag = context.runtime_state_store.get_session_tag(session_id)
        if not requested:
            lines = [
                "Usage: /tag <tag-name>",
                "",
                f"current_tag: {current_tag or '(none)'}",
                "Run the same command again to remove the current tag.",
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:tag",
                dialog_title="Tag",
                dialog_lines=lines,
            )
        if current_tag == requested:
            context.runtime_state_store.set_session_tag(session_id, None)
            return CommandResult(
                kind="message",
                message=f"Removed tag #{requested} from the current session.",
            )
        context.runtime_state_store.set_session_tag(session_id, requested)
        return CommandResult(
            kind="message",
            message=f"Tagged the current session with #{requested}.",
        )

    return SlashCommand(
        spec=CommandSpec(
            name="tag",
            description="Toggle a searchable tag on the current session.",
            command_type="local_ui",
            argument_hint="<tag-name>",
        ),
        usage="/tag <tag-name>",
        handler=handler,
    )


def _normalize_tag(value: str) -> str:
    collapsed = "-".join(part for part in value.strip().split() if part)
    safe = "".join(
        char.lower()
        for char in collapsed
        if char.isalnum() or char in {"-", "_", "."}
    )
    return safe.strip("-_.")
