from pathlib import Path

from claude_code_py.providers.plugins.marketplace import (
    find_marketplace_entry,
    install_project_plugin,
    load_marketplace_catalogs,
)
from claude_code_py.providers.plugins import load_plugins
from claude_code_py.skills.loader import load_skills


def test_load_plugins_discovers_project_and_cli_plugins(tmp_path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    workspace_root = tmp_path / "workspace"
    project_plugin = workspace_root / ".claude" / "plugins" / "reviewer"
    cli_plugin = tmp_path / "cli-plugin"
    project_plugin.mkdir(parents=True, exist_ok=True)
    cli_plugin.mkdir(parents=True, exist_ok=True)
    (project_plugin / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (project_plugin / ".claude-plugin" / "plugin.json").write_text(
        (
            '{'
            '"name":"reviewer-plugin",'
            '"commands":["./commands"],'
            '"skills":["./skills"]'
            '}'
        ),
        encoding="utf-8",
    )
    (project_plugin / "commands").mkdir(parents=True, exist_ok=True)
    (project_plugin / "skills").mkdir(parents=True, exist_ok=True)
    (cli_plugin / "commands").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Path, "home", lambda: home_dir)

    result = load_plugins(workspace_root, extra_plugin_dirs=[str(cli_plugin)])

    assert result.errors == []
    assert [plugin.name for plugin in result.plugins] == ["cli-plugin", "reviewer-plugin"]
    reviewer = next(plugin for plugin in result.plugins if plugin.name == "reviewer-plugin")
    assert reviewer.source_scope == "project"
    assert reviewer.command_paths == [project_plugin / "commands"]
    assert reviewer.skill_paths == [project_plugin / "skills"]


def test_load_skills_includes_plugin_skills(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    plugin_root = tmp_path / "demo-plugin"
    plugin_skill_dir = plugin_root / "skills"
    plugin_root.mkdir(parents=True, exist_ok=True)
    plugin_skill_dir.mkdir(parents=True, exist_ok=True)
    (plugin_root / "plugin.json").write_text(
        '{"name":"demo-plugin","skills":["./skills"]}',
        encoding="utf-8",
    )
    (plugin_skill_dir / "reviewer.md").write_text(
        (
            "---\n"
            "name: Reviewer Skill\n"
            "description: Plugin provided skill\n"
            "user-invocable: true\n"
            "---\n"
            "Review the current changes."
        ),
        encoding="utf-8",
    )

    plugin_result = load_plugins(workspace_root, extra_plugin_dirs=[str(plugin_root)])
    skills = load_skills(workspace_root, plugins=plugin_result.plugins)

    assert len(skills) == 1
    assert skills[0].command_name == "reviewer-skill"
    assert skills[0].source_scope == "plugin:demo-plugin"


def test_plugin_marketplace_catalogs_can_be_loaded_and_installed(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    source_plugin = tmp_path / "source-plugin"
    source_plugin.mkdir(parents=True, exist_ok=True)
    (source_plugin / "plugin.json").write_text(
        '{"name":"market-plugin","description":"Market plugin"}',
        encoding="utf-8",
    )
    catalog_dir = workspace_root / ".claude" / "marketplaces"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / "demo.json").write_text(
        (
            '{'
            '"name":"demo-market",'
            '"plugins":[{"name":"market-plugin","path":"'
            + str(source_plugin).replace("\\", "\\\\")
            + '","description":"Installable plugin","requires_trust":true}]'
            '}'
        ),
        encoding="utf-8",
    )

    catalogs = load_marketplace_catalogs(workspace_root, data_dir=tmp_path / "state")
    entry = find_marketplace_entry(catalogs, "demo-market:market-plugin")
    assert entry is not None
    installed = install_project_plugin(entry, workspace_root=workspace_root)

    assert catalogs[0].name == "demo-market"
    assert entry.requires_trust is True
    assert installed.exists() is True
    assert (installed / "plugin.json").exists() is True
