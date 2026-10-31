from datetime import UTC, datetime
from pathlib import Path
import gc
import tracemalloc

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_heapdump_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        del context, invocation
        if not tracemalloc.is_tracing():
            tracemalloc.start(25)
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")[:50]
        desktop = Path.home() / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        path = desktop / (
            "claude-code-py-heapdump-"
            + datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            + ".txt"
        )
        lines = [
            "claude-code-py heap dump",
            "",
            f"gc_objects: {len(gc.get_objects())}",
            "",
            "Top allocations:",
        ]
        lines.extend(str(stat) for stat in top_stats)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return CommandResult(
            kind="message",
            message=str(path),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="heapdump",
            description="Dump the Python heap snapshot to ~/Desktop.",
            command_type="local_ui",
        ),
        usage="/heapdump",
        handler=handler,
        hidden=True,
    )
