import sys
from pathlib import Path
from typing import Annotated

import typer

from claude_code_py import __version__
from claude_code_py.app.lifecycle import app_lifecycle
from claude_code_py.application.session_service import SessionService
from claude_code_py.cli.print_mode import OutputFormat, PrintModeParams, run_print_mode
from claude_code_py.cli.repl_mode import ReplModeParams, run_repl_mode
from claude_code_py.cli.textual_mode import run_textual_mode
from claude_code_py.domain.permissions import PermissionMode, normalize_permission_mode
from claude_code_py.providers.storage.session_index import SqliteSessionIndex
from claude_code_py.providers.storage.transcript_store import JsonlTranscriptStore

app = typer.Typer(
    help="Independent Python rewrite skeleton for Claude Code.",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def _permission_mode_callback(value: str) -> PermissionMode:
    try:
        return normalize_permission_mode(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _stdin_is_tty() -> bool:
    return sys.stdin.isatty()


@app.callback()
def main_callback(
    prompt_parts: Annotated[
        list[str] | None,
        typer.Argument(
            help="Prompt text or built-in command name.",
            show_default=False,
        ),
    ] = None,
    print_mode: Annotated[
        bool,
        typer.Option(
            "--print",
            "-p",
            help="Run in headless mode and print the result.",
        ),
    ] = False,
    textual_mode: Annotated[
        bool,
        typer.Option(
            "--textual",
            "--tui",
            help="Run the experimental Textual terminal UI shell.",
        ),
    ] = False,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Override the model for this invocation."),
    ] = None,
    session_id: Annotated[
        str | None,
        typer.Option(
            "--session-id",
            help="Reuse or create a specific headless session id.",
        ),
    ] = None,
    resume_session_id: Annotated[
        str | None,
        typer.Option(
            "--resume",
            "-r",
            help="Resume a specific session id.",
        ),
    ] = None,
    continue_session: Annotated[
        bool,
        typer.Option(
            "--continue",
            "-c",
            help="Continue the most recent session in the current project.",
        ),
    ] = False,
    fork_session: Annotated[
        bool,
        typer.Option(
            "--fork-session",
            help="Fork a resumed/continued session into a new session id.",
        ),
    ] = False,
    mcp_config: Annotated[
        list[str] | None,
        typer.Option(
            "--mcp-config",
            help="Load MCP servers from JSON files or JSON strings. Repeatable.",
        ),
    ] = None,
    plugin_dir: Annotated[
        list[str] | None,
        typer.Option(
            "--plugin-dir",
            help="Load local plugins from these directories. Repeatable.",
        ),
    ] = None,
    permission_mode: Annotated[
        str,
        typer.Option(
            "--permission-mode",
            help="Permission mode for tool execution.",
            callback=_permission_mode_callback,
        ),
    ] = "default",
    allow_tool: Annotated[
        list[str] | None,
        typer.Option(
            "--allow-tool",
            "--allowed-tools",
            "--allowedTools",
            help="Permission allow rule. Repeatable, e.g. --allow-tool Read(path:*)",
        ),
    ] = None,
    deny_tool: Annotated[
        list[str] | None,
        typer.Option(
            "--deny-tool",
            "--disallowed-tools",
            "--disallowedTools",
            help=(
                "Permission deny rule. Repeatable, "
                "e.g. --deny-tool Bash(command_prefix:rm)"
            ),
        ),
    ] = None,
    ask_tool: Annotated[
        list[str] | None,
        typer.Option(
            "--ask-tool",
            help=(
                "Permission ask rule. Repeatable, "
                "e.g. --ask-tool WebFetch(domain:github.com)"
            ),
        ),
    ] = None,
    system_prompt: Annotated[
        str | None,
        typer.Option("--system-prompt", help="Override the system prompt."),
    ] = None,
    system_prompt_file: Annotated[
        Path | None,
        typer.Option(
            "--system-prompt-file",
            help="Read the system prompt from a file.",
        ),
    ] = None,
    append_system_prompt: Annotated[
        str | None,
        typer.Option(
            "--append-system-prompt",
            help="Append additional text to the system prompt.",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--output-format",
            help="Output format for --print mode.",
            case_sensitive=False,
        ),
    ] = OutputFormat.TEXT,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            help="Show the installed claude_code_py version.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    del version
    tokens = prompt_parts or []
    prompt = " ".join(tokens).strip() or None

    if print_mode and textual_mode:
        typer.echo(
            "Error: --print and --textual cannot be combined.",
            err=True,
        )
        raise typer.Exit(code=1)

    if print_mode:
        with app_lifecycle() as container:
            exit_code, rendered = run_print_mode(
                container,
                PrintModeParams(
                    prompt=prompt,
                    session_id=session_id,
                    resume_session_id=resume_session_id,
                    continue_session=continue_session,
                    fork_session=fork_session,
                    mcp_configs=mcp_config or [],
                    plugin_dirs=plugin_dir or [],
                    model=model,
                    permission_mode=permission_mode,
                    allow_rules=allow_tool or [],
                    deny_rules=deny_tool or [],
                    ask_rules=ask_tool or [],
                    system_prompt=system_prompt,
                    system_prompt_file=system_prompt_file,
                    append_system_prompt=append_system_prompt,
                    output_format=output_format,
                ),
                stdin=sys.stdin,
            )
        if rendered:
            typer.echo(rendered)
        raise typer.Exit(code=exit_code)

    if tokens:
        command_name = tokens[0]
        if command_name == "doctor" and len(tokens) == 1:
            doctor()
            return
        if command_name == "version" and len(tokens) == 1:
            version_command()
            return
        if command_name == "sessions":
            limit = _parse_sessions_limit(tokens[1] if len(tokens) > 1 else None)
            sessions_command(limit=limit)
            return

    if prompt is not None and not textual_mode:
        typer.echo(
            "Error: interactive mode is not implemented yet. Use -p/--print.",
            err=True,
        )
        raise typer.Exit(code=1)
    if not _stdin_is_tty():
        typer.echo(
            "Error: interactive mode requires a TTY. Use -p/--print for headless mode.",
            err=True,
        )
        raise typer.Exit(code=1)

    with app_lifecycle() as container:
        try:
            repl_params = ReplModeParams(
                initial_prompt=prompt if textual_mode else None,
                session_id=session_id,
                resume_session_id=resume_session_id,
                continue_session=continue_session,
                fork_session=fork_session,
                mcp_configs=mcp_config or [],
                plugin_dirs=plugin_dir or [],
                model=model,
                permission_mode=permission_mode,
                allow_rules=allow_tool or [],
                deny_rules=deny_tool or [],
                ask_rules=ask_tool or [],
                system_prompt=system_prompt,
                system_prompt_file=system_prompt_file,
                append_system_prompt=append_system_prompt,
            )
            exit_code = (
                run_textual_mode(container, repl_params)
                if textual_mode
                else run_repl_mode(container, repl_params)
            )
        except RuntimeError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
    raise typer.Exit(code=exit_code)


def doctor() -> None:
    with app_lifecycle() as container:
        typer.echo(f"app_name={container.settings.app_name}")
        typer.echo(f"project_root={container.paths.root}")
        typer.echo(f"data_dir={container.paths.data_dir}")
        typer.echo(f"default_model={container.settings.default_model}")
        typer.echo(f"debug={container.settings.debug}")


def version_command() -> None:
    typer.echo(__version__)


def sessions_command(limit: int = 20) -> None:
    with app_lifecycle() as container:
        service = SessionService(
            JsonlTranscriptStore(container.paths),
            SqliteSessionIndex(container.paths.session_index_path),
        )
        sessions = service.list_sessions(limit=limit)
    if not sessions:
        typer.echo("No sessions found.")
        return
    for session in sessions:
        updated_at = session.updated_at.isoformat(timespec="seconds")
        typer.echo(
            f"{session.session_id}\t{updated_at}\t{session.message_count}\t{session.title}",
        )


def _parse_sessions_limit(raw_value: str | None) -> int:
    if raw_value is None:
        return 20
    try:
        limit = int(raw_value)
    except ValueError as exc:
        raise typer.BadParameter("sessions limit must be an integer") from exc
    if limit <= 0:
        raise typer.BadParameter("sessions limit must be > 0")
    return limit


def main() -> None:
    app()
