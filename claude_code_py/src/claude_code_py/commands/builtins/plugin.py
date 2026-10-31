import shutil
from pathlib import Path

from claude_code_py.commands.loader import (
    CommandDialogAction,
    CommandContext,
    CommandResult,
    CommandSelectorOption,
    SlashCommand,
    SlashCommandInvocation,
)
from claude_code_py.domain.commands import CommandSpec
from claude_code_py.providers.plugins import load_plugin_from_path
from claude_code_py.providers.plugins.marketplace import (
    find_marketplace_entry,
    install_project_plugin,
    install_project_plugin_from_path,
    load_marketplace_catalogs,
    plugin_trust_key,
    validate_plugin_source,
)


def build_plugin_command() -> SlashCommand:
    def handler(context: CommandContext, invocation: SlashCommandInvocation) -> CommandResult:
        args = invocation.args.split(maxsplit=2)
        if not args or args[0] in {"list", "manage"}:
            lines = _render_plugin_list_lines(context)
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                selector_kind="selector:plugin",
                selector_title="Plugin Manager",
                selector_options=_build_plugin_selector_options(context),
            )

        action = args[0].lower()

        if action == "reload":
            context.reload_skills()
            lines = [
                "Plugins and skills reloaded.",
                "",
                *_render_plugin_list_lines(context),
            ]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:plugin",
                dialog_title="Plugins Reloaded",
                dialog_lines=lines,
            )

        if action == "show" and len(args) > 1:
            return _show_plugin(context, args[1].strip())

        if action == "errors":
            if not context.plugin_errors:
                return CommandResult(kind="message", message="No plugin load errors.")
            lines = ["Plugin errors:", *context.plugin_errors]
            return CommandResult(
                kind="message",
                message="\n".join(lines),
                dialog_kind="command:plugin-errors",
                dialog_title="Plugin Errors",
                dialog_lines=lines,
            )

        if action == "validate" and len(args) > 1:
            return _validate_plugin(context, args[1].strip())

        if action == "trust" and len(args) > 1:
            desired = True
            if len(args) > 2:
                desired = args[2].strip().lower() != "off"
            return _trust_plugin(context, args[1].strip(), desired=desired)

        if action == "trust-source" and len(args) > 1:
            desired = True
            if len(args) > 2:
                desired = args[2].strip().lower() != "off"
            return _trust_plugin_source(context, args[1].strip(), desired=desired)

        if action == "install" and len(args) > 1:
            return _install_plugin(context, args[1].strip())

        if action == "update" and len(args) > 1:
            return _update_plugin(context, args[1].strip())

        if action in {"remove", "uninstall"} and len(args) > 1:
            return _remove_plugin(context, args[1].strip())

        if action == "marketplace":
            return _marketplace_command(context, args[1:])

        return CommandResult(
            kind="error",
            message=(
                "Usage: /plugin, /plugin manage, /plugin reload, /plugin show <name>, "
                "/plugin validate <name|path>, /plugin trust <name> [on|off], "
                "/plugin trust-source <marketplace:name|path> [on|off], "
                "/plugin install <marketplace:name|path>, /plugin update <name>, "
                "/plugin remove <name>, /plugin marketplace, or /plugin errors"
            ),
        )

    return SlashCommand(
        spec=CommandSpec(
            name="plugin",
            description="Inspect, validate, install, and trust plugins.",
            command_type="local_ui",
            argument_hint="[manage|reload|show|validate|trust|trust-source|install|update|remove|marketplace|errors]",
            aliases=["plugins", "marketplace"],
        ),
        usage="/plugin [manage|reload|show|validate|trust|trust-source|install|update|remove|marketplace|errors]",
        handler=handler,
    )


def _render_plugin_list_lines(context: CommandContext) -> list[str]:
    if not context.plugins:
        lines = ["No plugins loaded."]
        if context.plugin_errors:
            lines.extend(f"error: {error}" for error in context.plugin_errors)
        lines.extend(_marketplace_summary_lines(context))
        return lines

    lines = ["Loaded plugins:"]
    for plugin in context.plugins:
        trust_status = "trusted" if _is_trusted(context, plugin) else "untrusted"
        risk = _plugin_risk(plugin)
        lines.append(
            f"{plugin.name} | scope={plugin.source_scope} | {trust_status} | risk={risk} | "
            f"commands={len(plugin.command_paths)} | skills={len(plugin.skill_paths)} | "
            f"hooks={len(plugin.manifest.hooks)} | agents={len(plugin.manifest.agents)}",
        )
    for error in context.plugin_errors:
        lines.append(f"error: {error}")
    lines.extend(["Use /plugin show <name> to inspect one plugin.", *_marketplace_summary_lines(context)])
    return lines


def _show_plugin(context: CommandContext, plugin_name: str) -> CommandResult:
    target = next((plugin for plugin in context.plugins if plugin.name == plugin_name), None)
    if target is None:
        return CommandResult(
            kind="error",
            message=f"Unknown plugin '{plugin_name}'.",
        )

    trust_status = "trusted" if _is_trusted(context, target) else "untrusted"
    risk = _plugin_risk(target)
    lines = [
        f"name: {target.name}",
        f"source_scope: {target.source_scope}",
        f"root_path: {target.root_path}",
        f"version: {target.manifest.version or '(none)'}",
        f"description: {target.manifest.description or '(none)'}",
        f"trust: {trust_status}",
        f"risk: {risk}",
        f"update_candidate: {_find_update_candidate(context, target.name) or '(none)'}",
        f"command_paths: {', '.join(str(path) for path in target.command_paths) or '(none)'}",
        f"skill_paths: {', '.join(str(path) for path in target.skill_paths) or '(none)'}",
        f"hooks: {', '.join(target.manifest.hooks) or '(none)'}",
        f"agents: {', '.join(target.manifest.agents) or '(none)'}",
    ]
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:plugin-show",
        dialog_title=f"Plugin: {target.name}",
        dialog_lines=lines,
        dialog_actions=[
            CommandDialogAction(label="Plugin Menu", command="/plugin"),
            CommandDialogAction(label="Reload Plugins", command="/plugin reload"),
            CommandDialogAction(
                label="Trust On" if trust_status == "untrusted" else "Trust Off",
                command=f"/plugin trust {target.name} {'on' if trust_status == 'untrusted' else 'off'}",
            ),
            CommandDialogAction(
                label="Update",
                command=f"/plugin update {target.name}",
            ),
            CommandDialogAction(
                label="Remove",
                command=f"/plugin remove {target.name}",
            ),
            *(
                [
                    CommandDialogAction(
                        label="View Errors",
                        command="/plugin errors",
                        description=f"{len(context.plugin_errors)} current error(s)",
                    )
                ]
                if context.plugin_errors
                else []
            ),
        ],
    )


def _validate_plugin(context: CommandContext, raw_target: str) -> CommandResult:
    plugin = next((item for item in context.plugins if item.name == raw_target), None)
    if plugin is not None:
        path = plugin.root_path
    else:
        path = Path(raw_target).expanduser()
        if not path.is_absolute():
            path = (context.workspace_root / path).resolve()
    report = validate_plugin_source(path)
    lines = [
        "Plugin validation:",
        f"path: {report['path']}",
        f"exists: {'yes' if report['exists'] else 'no'}",
        f"manifest_path: {report['manifest_path'] or '(missing)'}",
        f"has_commands_dir: {'yes' if report['has_commands_dir'] else 'no'}",
        f"has_skills_dir: {'yes' if report['has_skills_dir'] else 'no'}",
    ]
    if report["exists"]:
        try:
            loaded = load_plugin_from_path(path, source_scope="cli_arg")
            lines.extend(
                [
                    f"manifest_name: {loaded.name}",
                    f"version: {loaded.manifest.version or '(none)'}",
                    f"risk: {_plugin_risk(loaded)}",
                    f"trusted: {'yes' if _is_trusted(context, loaded) else 'no'}",
                    f"source_trusted: {'yes' if _is_source_trusted(context, path) else 'no'}",
                ]
            )
        except Exception as exc:
            lines.append(f"load_error: {exc}")
    return CommandResult(
        kind="message",
        message="\n".join(lines),
        dialog_kind="command:plugin-validate",
        dialog_title="Plugin Validation",
        dialog_lines=lines,
    )


def _trust_plugin(context: CommandContext, plugin_name: str, *, desired: bool) -> CommandResult:
    target = next((plugin for plugin in context.plugins if plugin.name == plugin_name), None)
    if target is None:
        return CommandResult(kind="error", message=f"Unknown plugin '{plugin_name}'.")
    key = plugin_trust_key(target.root_path)
    context.runtime_state_store.set_plugin_trusted(key, desired)
    return CommandResult(
        kind="message",
        message=f"Plugin trust updated: {plugin_name} -> {'trusted' if desired else 'untrusted'}.",
    )


def _trust_plugin_source(
    context: CommandContext,
    raw_target: str,
    *,
    desired: bool,
) -> CommandResult:
    entry = find_marketplace_entry(
        load_marketplace_catalogs(
            context.workspace_root,
            data_dir=context.container.paths.data_dir,
        ),
        raw_target,
    )
    if entry is not None:
        path = entry.source_path
        label = entry.qualified_name
    else:
        path = Path(raw_target).expanduser()
        if not path.is_absolute():
            path = (context.workspace_root / path).resolve()
        label = str(path)
    context.runtime_state_store.set_plugin_trusted(
        plugin_trust_key(path),
        desired,
    )
    return CommandResult(
        kind="message",
        message=f"Plugin source trust updated: {label} -> {'trusted' if desired else 'untrusted'}.",
    )


def _install_plugin(context: CommandContext, raw_target: str) -> CommandResult:
    catalogs = load_marketplace_catalogs(
        context.workspace_root,
        data_dir=context.container.paths.data_dir,
    )
    source_path: Path | None = None
    entry = find_marketplace_entry(catalogs, raw_target)
    install_message = ""
    if entry is not None:
        if entry.requires_trust and not _is_source_trusted(context, entry.source_path):
            return CommandResult(
                kind="error",
                message=(
                    f"Marketplace plugin {entry.qualified_name} requires trust before install. "
                    f"Run /plugin trust-source {entry.qualified_name} on"
                ),
            )
        source_path = install_project_plugin(entry, workspace_root=context.workspace_root)
        if _is_source_trusted(context, entry.source_path):
            context.runtime_state_store.set_plugin_trusted(
                plugin_trust_key(source_path),
                True,
            )
        install_message = f"Installed marketplace plugin {entry.qualified_name} into {source_path}."
    else:
        direct = Path(raw_target).expanduser()
        if not direct.is_absolute():
            direct = (context.workspace_root / direct).resolve()
        loaded = load_plugin_from_path(direct, source_scope="cli_arg")
        if _plugin_risk(loaded) != "normal" and not _is_source_trusted(context, direct):
            return CommandResult(
                kind="error",
                message=(
                    f"Plugin source {direct} contains sensitive capabilities ({_plugin_risk(loaded)}). "
                    f"Run /plugin trust-source {direct} on before install."
                ),
            )
        source_path = install_project_plugin_from_path(
            direct,
            plugin_name=loaded.name,
            workspace_root=context.workspace_root,
        )
        if _is_source_trusted(context, direct):
            context.runtime_state_store.set_plugin_trusted(
                plugin_trust_key(source_path),
                True,
            )
        install_message = f"Installed local plugin {loaded.name} into {source_path}."

    context.reload_skills()
    return CommandResult(
        kind="message",
        message=install_message,
    )


def _update_plugin(context: CommandContext, plugin_name: str) -> CommandResult:
    target = next((plugin for plugin in context.plugins if plugin.name == plugin_name), None)
    if target is None:
        return CommandResult(kind="error", message=f"Unknown plugin '{plugin_name}'.")

    entry = find_marketplace_entry(
        load_marketplace_catalogs(
            context.workspace_root,
            data_dir=context.container.paths.data_dir,
        ),
        plugin_name,
    )
    if entry is None:
        return CommandResult(
            kind="error",
            message=f"No marketplace update source found for '{plugin_name}'.",
        )
    if entry.requires_trust and not _is_source_trusted(context, entry.source_path):
        return CommandResult(
            kind="error",
            message=(
                f"Marketplace plugin {entry.qualified_name} requires trust before update. "
                f"Run /plugin trust-source {entry.qualified_name} on"
            ),
        )
    installed_path = install_project_plugin(entry, workspace_root=context.workspace_root)
    if _is_source_trusted(context, entry.source_path):
        context.runtime_state_store.set_plugin_trusted(
            plugin_trust_key(installed_path),
            True,
        )
    context.reload_skills()
    return CommandResult(
        kind="message",
        message=f"Updated plugin {plugin_name} from {entry.qualified_name}.",
    )


def _remove_plugin(context: CommandContext, plugin_name: str) -> CommandResult:
    target = next((plugin for plugin in context.plugins if plugin.name == plugin_name), None)
    if target is None:
        return CommandResult(kind="error", message=f"Unknown plugin '{plugin_name}'.")
    project_root = (context.workspace_root / ".claude" / "plugins").resolve()
    try:
        target.root_path.resolve().relative_to(project_root)
    except ValueError:
        return CommandResult(
            kind="error",
            message=(
                f"Plugin '{plugin_name}' is not installed in the project plugin directory "
                "and cannot be removed by this command."
            ),
        )
    shutil.rmtree(target.root_path)
    context.runtime_state_store.set_plugin_trusted(
        plugin_trust_key(target.root_path),
        False,
    )
    context.reload_skills()
    return CommandResult(
        kind="message",
        message=f"Removed plugin {plugin_name}.",
    )


def _marketplace_command(context: CommandContext, args: list[str]) -> CommandResult:
    catalogs = load_marketplace_catalogs(
        context.workspace_root,
        data_dir=context.container.paths.data_dir,
    )
    if not args:
        lines = _marketplace_summary_lines(context)
        if len(lines) == 1:
            lines.append("No marketplace catalogs available.")
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:plugin-marketplace",
            dialog_title="Plugin Marketplace",
            dialog_lines=lines,
            selector_kind="selector:plugin-marketplace",
            selector_title="Marketplace Plugins",
            selector_options=[
                CommandSelectorOption(
                    label=entry.qualified_name,
                    command=f"/plugin install {entry.qualified_name}",
                    description=_marketplace_entry_description(context, entry),
                    preview_lines=[
                        f"marketplace: {catalog.name}",
                        f"path: {entry.source_path}",
                        f"version: {entry.version or '(none)'}",
                        f"requires_trust: {'yes' if entry.requires_trust else 'no'}",
                        f"source_trusted: {'yes' if _is_source_trusted(context, entry.source_path) else 'no'}",
                        f"installed: {'yes' if _is_installed(context, entry.name) else 'no'}",
                    ],
                )
                for catalog in catalogs
                for entry in catalog.plugins
            ]
            or None,
        )
    if args[0] == "show" and len(args) > 1:
        entry = find_marketplace_entry(catalogs, args[1].strip())
        if entry is None:
            return CommandResult(
                kind="error",
                message=f"Unknown marketplace plugin '{args[1].strip()}'.",
            )
        lines = [
            f"name: {entry.name}",
            f"marketplace: {entry.marketplace_name}",
            f"description: {entry.description or '(none)'}",
            f"version: {entry.version or '(none)'}",
            f"source_path: {entry.source_path}",
            f"requires_trust: {'yes' if entry.requires_trust else 'no'}",
            f"source_trusted: {'yes' if _is_source_trusted(context, entry.source_path) else 'no'}",
            f"installed: {'yes' if _is_installed(context, entry.name) else 'no'}",
        ]
        return CommandResult(
            kind="message",
            message="\n".join(lines),
            dialog_kind="command:plugin-marketplace-show",
            dialog_title=f"Marketplace Plugin: {entry.qualified_name}",
            dialog_lines=lines,
            dialog_actions=[
                CommandDialogAction(label="Install", command=f"/plugin install {entry.qualified_name}"),
                CommandDialogAction(label="Trust Source", command=f"/plugin trust-source {entry.qualified_name} on"),
            ],
        )
    return CommandResult(kind="error", message="Usage: /plugin marketplace [show <marketplace:name>]")


def _marketplace_summary_lines(context: CommandContext) -> list[str]:
    catalogs = load_marketplace_catalogs(
        context.workspace_root,
        data_dir=context.container.paths.data_dir,
    )
    lines = [f"marketplaces: {len(catalogs)}"]
    if not catalogs:
        return lines
    for catalog in catalogs:
        lines.append(
            f"{catalog.name} | source={catalog.source_path} | plugins={len(catalog.plugins)}"
        )
        for entry in catalog.plugins[:8]:
            lines.append(
                f"  - {entry.qualified_name} | trust_required={'yes' if entry.requires_trust else 'no'} | "
                f"installed={'yes' if _is_installed(context, entry.name) else 'no'}"
            )
    return lines


def _build_plugin_selector_options(context: CommandContext) -> list[CommandSelectorOption]:
    options: list[CommandSelectorOption] = []
    for plugin in context.plugins:
        trust_status = "trusted" if _is_trusted(context, plugin) else "untrusted"
        options.append(
            CommandSelectorOption(
                label=plugin.name,
                command=f"/plugin show {plugin.name}",
                description=(
                    f"{trust_status} | {_plugin_risk(plugin)}"
                ),
                preview_lines=_build_plugin_preview_lines(context, plugin),
            )
        )

    options.extend(
        [
            CommandSelectorOption(
                label="Reload Plugins",
                command="/plugin reload",
                description="Rescan plugin manifests, commands, and skills from disk.",
                preview_lines=[
                    "Reload plugin manifests from user, project, and CLI plugin directories.",
                    "This also refreshes skills and plugin-provided slash commands.",
                ],
            ),
            CommandSelectorOption(
                label="Marketplace",
                command="/plugin marketplace",
                description="Browse available marketplace plugin catalogs.",
                preview_lines=_marketplace_summary_lines(context),
            ),
            CommandSelectorOption(
                label="Installed Plugin Validation",
                command="/plugin",
                description="Use /plugin validate <name> to inspect plugin safety and structure.",
                preview_lines=["Validate plugin manifests, commands, skills, and trust state."],
            ),
        ]
    )

    if context.plugin_errors:
        options.append(
            CommandSelectorOption(
                label=f"Plugin Errors ({len(context.plugin_errors)})",
                command="/plugin errors",
                description="Inspect plugin load failures.",
                preview_lines=[
                    "Current plugin load errors:",
                    *context.plugin_errors[:8],
                    *(
                        [f"... {len(context.plugin_errors) - 8} more error(s)"]
                        if len(context.plugin_errors) > 8
                        else []
                    ),
                ],
            )
        )

    return options


def _build_plugin_preview_lines(context: CommandContext, plugin) -> list[str]:
    preview_lines = [
        f"scope: {plugin.source_scope}",
        f"version: {plugin.manifest.version or '(none)'}",
        f"root_path: {plugin.root_path}",
        f"trust: {'trusted' if _is_trusted(context, plugin) else 'untrusted'}",
        f"risk: {_plugin_risk(plugin)}",
        f"command_paths: {len(plugin.command_paths)}",
        f"skill_paths: {len(plugin.skill_paths)}",
        f"hooks: {', '.join(plugin.manifest.hooks) or '(none)'}",
        f"agents: {', '.join(plugin.manifest.agents) or '(none)'}",
    ]
    if plugin.command_paths:
        preview_lines.extend(
            [
                "",
                "commands:",
                *[str(path) for path in plugin.command_paths[:4]],
            ]
        )
    if plugin.skill_paths:
        preview_lines.extend(
            [
                "",
                "skills:",
                *[str(path) for path in plugin.skill_paths[:4]],
            ]
        )
    return preview_lines


def _plugin_risk(plugin) -> str:
    risks = []
    if plugin.manifest.hooks:
        risks.append("hooks")
    if plugin.manifest.agents:
        risks.append("agents")
    return ",".join(risks) or "normal"


def _is_trusted(context: CommandContext, plugin) -> bool:
    return context.runtime_state_store.is_plugin_trusted(
        plugin_trust_key(plugin.root_path)
    )


def _is_source_trusted(context: CommandContext, path: Path) -> bool:
    return context.runtime_state_store.is_plugin_trusted(
        plugin_trust_key(path)
    )


def _find_update_candidate(context: CommandContext, plugin_name: str) -> str | None:
    entry = find_marketplace_entry(
        load_marketplace_catalogs(
            context.workspace_root,
            data_dir=context.container.paths.data_dir,
        ),
        plugin_name,
    )
    return entry.qualified_name if entry is not None else None


def _is_installed(context: CommandContext, plugin_name: str) -> bool:
    return any(plugin.name == plugin_name for plugin in context.plugins)


def _marketplace_entry_description(context: CommandContext, entry) -> str:
    bits = []
    if entry.requires_trust:
        bits.append("trust required")
    if _is_installed(context, entry.name):
        bits.append("installed")
    if not bits:
        bits.append("available")
    return " | ".join(bits)
