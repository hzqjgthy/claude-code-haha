import shlex

from claude_code_py.commands.loader import (
    CommandContext,
    CommandResult,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec


def build_diff_command() -> SlashCommand:
    def handler(
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        shell_provider = context.tool_context.shell_provider
        if shell_provider is None:
            return CommandResult(
                kind="error",
                message="Diff requires a configured shell provider.",
            )

        args = invocation.args.strip()
        full_view = False
        target_path = ""
        if args:
            parts = args.split(maxsplit=1)
            if parts[0] == "full":
                full_view = True
                target_path = parts[1].strip() if len(parts) > 1 else ""
            else:
                target_path = args

        quoted_path = f" -- {shlex.quote(target_path)}" if target_path else ""
        probe = shell_provider.run(
            "git rev-parse --is-inside-work-tree",
            cwd=context.workspace_root,
            timeout=10,
        )
        if probe.exit_code != 0 or probe.stdout.strip() != "true":
            return CommandResult(
                kind="message",
                message="Current workspace is not inside a git repository.",
            )

        status = shell_provider.run(
            f"git status --short{quoted_path}",
            cwd=context.workspace_root,
            timeout=10,
        )
        staged = shell_provider.run(
            f"git diff --cached {'--stat' if not full_view else ''}{quoted_path}",
            cwd=context.workspace_root,
            timeout=20,
        )
        unstaged = shell_provider.run(
            f"git diff {'--stat' if not full_view else ''}{quoted_path}",
            cwd=context.workspace_root,
            timeout=20,
        )

        if (
            not status.stdout.strip()
            and not staged.stdout.strip()
            and not unstaged.stdout.strip()
        ):
            return CommandResult(
                kind="message",
                message="Working tree is clean.",
            )

        lines = ["Git diff:"]
        if target_path:
            lines.append(f"path_filter: {target_path}")
        if status.stdout.strip():
            lines.extend(["", "status:", status.stdout.rstrip()])
        if staged.stdout.strip():
            lines.extend(
                [
                    "",
                    "staged diff:" if full_view else "staged diff stat:",
                    staged.stdout.rstrip(),
                ]
            )
        if unstaged.stdout.strip():
            lines.extend(
                [
                    "",
                    "unstaged diff:" if full_view else "unstaged diff stat:",
                    unstaged.stdout.rstrip(),
                ]
            )
        if not full_view:
            lines.append("")
            lines.append("Use /diff full to inspect the full patch.")
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:diff",
            dialog_title="Diff",
            dialog_lines=lines,
        )

    return SlashCommand(
        spec=CommandSpec(
            name="diff",
            description="Inspect git working tree differences for the workspace.",
            command_type="local_ui",
            argument_hint="[full] [path]",
        ),
        usage="/diff [full] [path]",
        handler=handler,
    )
