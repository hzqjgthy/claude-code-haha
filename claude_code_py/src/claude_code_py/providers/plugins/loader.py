import json
from pathlib import Path

from pydantic import BaseModel, Field

from claude_code_py.providers.plugins.manifest import (
    LoadedPlugin,
    PluginManifest,
    PluginSourceScope,
)


class PluginLoadResult(BaseModel):
    plugins: list[LoadedPlugin] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def load_plugins(
    workspace_root: Path,
    *,
    extra_plugin_dirs: list[str] | None = None,
) -> PluginLoadResult:
    loaded: dict[str, LoadedPlugin] = {}
    errors: list[str] = []

    for scope, path in iter_plugin_candidates(workspace_root, extra_plugin_dirs):
        try:
            plugin = load_plugin_from_path(path, source_scope=scope)
        except Exception as exc:
            errors.append(f"Failed to load plugin at {path}: {exc}")
            continue
        loaded[plugin.name] = plugin

    return PluginLoadResult(
        plugins=sorted(loaded.values(), key=lambda plugin: plugin.name),
        errors=errors,
    )


def iter_plugin_candidates(
    workspace_root: Path,
    extra_plugin_dirs: list[str] | None,
) -> list[tuple[PluginSourceScope, Path]]:
    candidates: list[tuple[PluginSourceScope, Path]] = []
    for scope, root in [
        ("user", Path.home() / ".claude" / "plugins"),
        ("project", workspace_root / ".claude" / "plugins"),
    ]:
        if not root.exists():
            continue
        for path in sorted(root.iterdir()):
            if path.is_dir():
                candidates.append((scope, path))
    for raw_path in extra_plugin_dirs or []:
        path = Path(raw_path).expanduser().resolve()
        if path.is_dir():
            candidates.append(("cli_arg", path))
    return candidates


def load_plugin_from_path(
    plugin_root: Path,
    *,
    source_scope: PluginSourceScope,
) -> LoadedPlugin:
    plugin_root = plugin_root.resolve()
    manifest = load_plugin_manifest(plugin_root)
    command_paths = resolve_component_paths(
        plugin_root,
        manifest.commands,
        default_path=plugin_root / "commands",
    )
    skill_paths = resolve_component_paths(
        plugin_root,
        manifest.skills,
        default_path=plugin_root / "skills",
    )
    return LoadedPlugin(
        name=manifest.name,
        root_path=plugin_root,
        source_scope=source_scope,
        manifest=manifest,
        command_paths=command_paths,
        skill_paths=skill_paths,
    )


def load_plugin_manifest(plugin_root: Path) -> PluginManifest:
    manifest_candidates = [
        plugin_root / ".claude-plugin" / "plugin.json",
        plugin_root / "plugin.json",
    ]
    for path in manifest_candidates:
        if not path.exists():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Plugin manifest must be a JSON object: {path}")
        return PluginManifest.model_validate(raw)
    return PluginManifest(name=plugin_root.name)


def resolve_component_paths(
    plugin_root: Path,
    manifest_paths: list[str],
    *,
    default_path: Path,
) -> list[Path]:
    resolved_paths: list[Path] = []
    seen: set[Path] = set()
    candidates = [*manifest_paths] if manifest_paths else []
    if not candidates and default_path.exists():
        candidates = [str(default_path.relative_to(plugin_root))]

    for relative_path in candidates:
        path = (plugin_root / relative_path).resolve()
        try:
            path.relative_to(plugin_root)
        except ValueError as exc:
            raise ValueError(
                f"Plugin path '{relative_path}' escapes plugin root '{plugin_root}'.",
            ) from exc
        if not path.exists():
            continue
        if path in seen:
            continue
        seen.add(path)
        resolved_paths.append(path)
    return resolved_paths
