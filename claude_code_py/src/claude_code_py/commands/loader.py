from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from claude_code_py.app.container import AppContainer
from claude_code_py.application.permission_service import PermissionService
from claude_code_py.commands.markdown import (
    MarkdownCommandDefinition,
    iter_markdown_command_files,
    parse_markdown_command,
)
from claude_code_py.application.task_service import TaskService
from claude_code_py.application.session_service import SessionService
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.domain.sessions import SessionState
from claude_code_py.providers.mcp import LoadedMcpServerConfig, McpConnectionManager, McpToolDefinition
from claude_code_py.providers.plugins.manifest import LoadedPlugin
from claude_code_py.providers.plugins.loader import load_plugins
from claude_code_py.providers.remote import RemoteProvider
from claude_code_py.providers.remote.session_manager import RemoteSessionManager
from claude_code_py.providers.storage import RuntimeStateStore
from claude_code_py.skills.loader import load_skills
from claude_code_py.skills.parser import SkillDefinition
from claude_code_py.tools.base import ToolContext
from claude_code_py.ui.prompt_toolkit import PromptToolkitReplTerminal, ReplStatus

CommandResultKind = Literal["message", "prompt", "noop", "error"]
CommandHandler = Callable[["CommandContext", "SlashCommandInvocation"], "CommandResult"]


@dataclass(slots=True)
class CommandDialogAction:
    label: str
    command: str
    description: str | None = None


@dataclass(slots=True)
class CommandSelectorOption:
    label: str
    command: str
    description: str | None = None
    preview_lines: list[str] | None = None


@dataclass(slots=True)
class SlashCommandInvocation:
    name: str
    args: str
    raw: str


@dataclass(slots=True)
class CommandResult:
    kind: CommandResultKind
    message: str | None = None
    prompt: str | None = None
    transient_system_prompt: str | None = None
    terminate_session: bool = False
    refresh_transcript: bool = False
    dialog_kind: str | None = None
    dialog_title: str | None = None
    dialog_lines: list[str] | None = None
    dialog_actions: list[CommandDialogAction] | None = None
    selector_kind: str | None = None
    selector_title: str | None = None
    selector_options: list[CommandSelectorOption] | None = None
    editor_kind: str | None = None
    editor_title: str | None = None
    editor_path: str | None = None
    editor_text: str | None = None
    editor_language: str | None = None


@dataclass(slots=True)
class SlashCommand:
    spec: CommandSpec
    usage: str
    handler: CommandHandler
    source: str = "builtin"
    hidden: bool = False


@dataclass(slots=True)
class CommandContext:
    container: AppContainer
    session_service: SessionService
    task_service: TaskService
    permission_service: PermissionService
    terminal: PromptToolkitReplTerminal
    workspace_root: Path
    tool_context: ToolContext
    session_state: SessionState
    model_name: str
    permission_mode: str
    base_system_prompt: str | None
    plugin_dirs: list[str]
    plugins: list[LoadedPlugin]
    plugin_errors: list[str]
    skills: list[SkillDefinition]
    mcp_server_configs: list[LoadedMcpServerConfig]
    mcp_tool_definitions: list[McpToolDefinition]
    mcp_manager: McpConnectionManager
    remote_provider: RemoteProvider | None
    remote_session_manager: RemoteSessionManager | None
    runtime_state_store: RuntimeStateStore
    command_registry: "CommandRegistry"

    def bind_status(self) -> None:
        self.terminal.bind_status(
            ReplStatus(
                session_id=self.session_state.metadata.session_id,
                model=self.model_name,
                permission_mode=self.permission_mode,
            ),
        )

    def reload_skills(self) -> list[SkillDefinition]:
        plugin_result = load_plugins(
            self.workspace_root,
            extra_plugin_dirs=self.plugin_dirs,
        )
        self.plugins = plugin_result.plugins
        self.plugin_errors = plugin_result.errors
        self.skills = load_skills(self.workspace_root, plugins=self.plugins)
        self.command_registry = build_command_registry(
            self.skills,
            plugin_commands=build_plugin_commands(self.plugins),
        )
        return self.skills


class CommandRegistry:
    def __init__(self, commands: list[SlashCommand]) -> None:
        self._commands: dict[str, SlashCommand] = {}
        self._command_list = list(commands)
        for command in commands:
            self._commands[command.spec.name] = command
            for alias in command.spec.aliases:
                self._commands[alias] = command

    def get(self, name: str) -> SlashCommand | None:
        return self._commands.get(name)

    def list_commands(self) -> list[SlashCommand]:
        return sorted(
            self._command_list,
            key=lambda command: command.spec.name,
        )

    def execute(
        self,
        context: CommandContext,
        invocation: SlashCommandInvocation,
    ) -> CommandResult:
        command = self.get(invocation.name)
        if command is None:
            return CommandResult(
                kind="error",
                message=f"Unknown slash command '/{invocation.name}'. Use /help.",
            )
        return command.handler(context, invocation)


def parse_slash_command(text: str) -> SlashCommandInvocation | None:
    if not text.startswith("/"):
        return None
    body = text[1:].strip()
    if not body:
        return SlashCommandInvocation(name="help", args="", raw=text)
    parts = body.split(maxsplit=1)
    name = parts[0].strip().lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    return SlashCommandInvocation(name=name, args=args, raw=text)


def build_command_registry(
    skills: list[SkillDefinition],
    *,
    plugin_commands: list[SlashCommand] | None = None,
) -> CommandRegistry:
    from claude_code_py.commands.builtins import build_builtin_commands

    commands = [*build_builtin_commands()]
    for skill in skills:
        if skill.user_invocable:
            commands.append(build_skill_command(skill))
    commands.extend(plugin_commands or [])
    return CommandRegistry(commands)


def build_skill_command(skill: SkillDefinition) -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        user_request = invocation.args.strip() or (
            f"Apply the '{skill.name}' skill to the current task."
        )
        skill_system_prompt = "\n\n".join(
            part
            for part in [
                context.base_system_prompt,
                f"Skill name: {skill.name}",
                f"Skill description: {skill.description}" if skill.description else None,
                f"When to use: {skill.when_to_use}" if skill.when_to_use else None,
                "Follow the skill instructions below:",
                skill.content,
            ]
            if part
        )
        return CommandResult(
            kind="prompt",
            prompt=user_request,
            transient_system_prompt=skill_system_prompt,
        )

    return SlashCommand(
        spec=CommandSpec(
            name=skill.command_name,
            description=skill.description or f"Run the {skill.name} skill.",
            command_type="prompt",
        ),
        usage=f"/{skill.command_name} {skill.argument_hint or '[request]'}",
        handler=handler,
        source=f"skill:{skill.source_scope}",
    )


def build_plugin_commands(plugins: list[LoadedPlugin]) -> list[SlashCommand]:
    commands: list[SlashCommand] = []
    for plugin in plugins:
        for root in plugin.command_paths:
            for path in iter_markdown_command_files(root):
                definition = parse_markdown_command(
                    path.read_text(encoding="utf-8"),
                    source_path=path,
                    source_scope=f"plugin:{plugin.name}",
                )
                commands.append(build_markdown_prompt_command(definition))
    return commands


def build_markdown_prompt_command(
    definition: MarkdownCommandDefinition,
) -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        user_request = invocation.args.strip() or (
            f"Run the '{definition.name}' command for the current task."
        )
        command_system_prompt = "\n\n".join(
            part
            for part in [
                context.base_system_prompt,
                f"Command name: {definition.name}",
                (
                    f"Command description: {definition.description}"
                    if definition.description
                    else None
                ),
                (
                    f"When to use: {definition.when_to_use}"
                    if definition.when_to_use
                    else None
                ),
                "Follow the command instructions below:",
                definition.content,
            ]
            if part
        )
        return CommandResult(
            kind="prompt",
            prompt=user_request,
            transient_system_prompt=command_system_prompt,
        )

    return SlashCommand(
        spec=CommandSpec(
            name=definition.command_name,
            description=definition.description or f"Run the {definition.name} command.",
            command_type="prompt",
        ),
        usage=f"/{definition.command_name} {definition.argument_hint or '[request]'}",
        handler=handler,
        source=definition.source_scope,
    )
