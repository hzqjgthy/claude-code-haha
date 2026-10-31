from __future__ import annotations

import json
import shutil
from pathlib import Path

from pydantic import BaseModel, Field


class MarketplacePluginEntry(BaseModel):
    marketplace_name: str
    name: str
    description: str | None = None
    version: str | None = None
    source_path: Path
    requires_trust: bool = False

    @property
    def qualified_name(self) -> str:
        return f"{self.marketplace_name}:{self.name}"


class MarketplaceCatalog(BaseModel):
    name: str
    source_path: Path
    plugins: list[MarketplacePluginEntry] = Field(default_factory=list)


def load_marketplace_catalogs(
    workspace_root: Path,
    *,
    data_dir: Path,
) -> list[MarketplaceCatalog]:
    catalogs: list[MarketplaceCatalog] = []
    for root in [
        workspace_root / ".claude" / "marketplaces",
        data_dir / "marketplaces",
    ]:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            catalogs.append(load_marketplace_catalog(path))
    return catalogs


def load_marketplace_catalog(path: Path) -> MarketplaceCatalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        name = path.stem
        entries = raw
    elif isinstance(raw, dict):
        name = str(raw.get("name") or path.stem)
        entries = raw.get("plugins", [])
    else:
        raise ValueError(f"Invalid marketplace catalog: {path}")
    if not isinstance(entries, list):
        raise ValueError(f"Invalid marketplace catalog entries: {path}")

    plugins: list[MarketplacePluginEntry] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        plugin_name = item.get("name")
        source = item.get("path") or item.get("source") or item.get("source_path")
        if not isinstance(plugin_name, str) or not plugin_name.strip():
            continue
        if not isinstance(source, str) or not source.strip():
            continue
        source_path = Path(source).expanduser()
        if not source_path.is_absolute():
            source_path = (path.parent / source_path).resolve()
        else:
            source_path = source_path.resolve()
        plugins.append(
            MarketplacePluginEntry(
                marketplace_name=name,
                name=plugin_name.strip(),
                description=item.get("description")
                if isinstance(item.get("description"), str)
                else None,
                version=item.get("version")
                if isinstance(item.get("version"), str)
                else None,
                source_path=source_path,
                requires_trust=bool(item.get("requires_trust", False)),
            )
        )
    return MarketplaceCatalog(name=name, source_path=path.resolve(), plugins=plugins)


def find_marketplace_entry(
    catalogs: list[MarketplaceCatalog],
    raw_name: str,
) -> MarketplacePluginEntry | None:
    normalized = raw_name.strip()
    if ":" in normalized:
        marketplace_name, plugin_name = normalized.split(":", maxsplit=1)
        for catalog in catalogs:
            if catalog.name != marketplace_name:
                continue
            for entry in catalog.plugins:
                if entry.name == plugin_name:
                    return entry
        return None
    matches = [entry for catalog in catalogs for entry in catalog.plugins if entry.name == normalized]
    if len(matches) == 1:
        return matches[0]
    return None


def install_project_plugin(
    entry: MarketplacePluginEntry,
    *,
    workspace_root: Path,
) -> Path:
    if not entry.source_path.exists():
        raise FileNotFoundError(f"Plugin source was not found: {entry.source_path}")
    target_root = workspace_root / ".claude" / "plugins" / entry.name
    target_root.parent.mkdir(parents=True, exist_ok=True)
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(entry.source_path, target_root)
    return target_root


def install_project_plugin_from_path(
    source_path: Path,
    *,
    plugin_name: str,
    workspace_root: Path,
) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"Plugin source was not found: {source_path}")
    target_root = workspace_root / ".claude" / "plugins" / plugin_name
    target_root.parent.mkdir(parents=True, exist_ok=True)
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(source_path, target_root)
    return target_root


def validate_plugin_source(path: Path) -> dict[str, object]:
    manifest_candidates = [
        path / ".claude-plugin" / "plugin.json",
        path / "plugin.json",
    ]
    manifest_path = next((candidate for candidate in manifest_candidates if candidate.exists()), None)
    return {
        "path": str(path.resolve()),
        "exists": path.exists(),
        "manifest_path": str(manifest_path.resolve()) if manifest_path is not None else None,
        "has_commands_dir": (path / "commands").exists(),
        "has_skills_dir": (path / "skills").exists(),
    }


def plugin_trust_key(path: Path) -> str:
    return str(path.resolve())
