from pathlib import Path

from claude_code_py.providers.plugins.manifest import LoadedPlugin
from claude_code_py.skills.parser import SkillDefinition, parse_skill_markdown


def load_skills(
    workspace_root: Path,
    *,
    plugins: list[LoadedPlugin] | None = None,
) -> list[SkillDefinition]:
    roots = [
        ("user", Path.home() / ".claude" / "skills"),
        ("project", workspace_root / ".claude" / "skills"),
    ]
    loaded: dict[str, SkillDefinition] = {}
    for scope, root in roots:
        for path in iter_skill_files(root):
            skill = parse_skill_markdown(
                path.read_text(encoding="utf-8"),
                source_path=path,
                source_scope=scope,
            )
            loaded[skill.command_name] = skill
    for plugin in plugins or []:
        for root in plugin.skill_paths:
            for path in iter_skill_files(root):
                skill = parse_skill_markdown(
                    path.read_text(encoding="utf-8"),
                    source_path=path,
                    source_scope=f"plugin:{plugin.name}",
                )
                loaded[skill.command_name] = skill
    return sorted(loaded.values(), key=lambda skill: skill.command_name)


def iter_skill_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.name == "SKILL.md" or root.suffix.lower() == ".md" else []
    if not root.exists():
        return []
    skill_files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "SKILL.md" or path.suffix.lower() == ".md":
            skill_files.append(path)
    return skill_files
