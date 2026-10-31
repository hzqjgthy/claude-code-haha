from pathlib import Path

from claude_code_py.skills.loader import load_skills


def test_load_skills_reads_project_and_user_scopes(tmp_path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    workspace_root = tmp_path / "workspace"
    user_skill_dir = home_dir / ".claude" / "skills" / "reviewer"
    project_skill_dir = workspace_root / ".claude" / "skills" / "reviewer"
    user_skill_dir.mkdir(parents=True, exist_ok=True)
    project_skill_dir.mkdir(parents=True, exist_ok=True)
    (user_skill_dir / "SKILL.md").write_text(
        "---\nname: Reviewer\ndescription: User skill\nuser-invocable: true\n---\nUser instructions",
        encoding="utf-8",
    )
    (project_skill_dir / "SKILL.md").write_text(
        "---\nname: Reviewer\ndescription: Project skill\nuser-invocable: true\nargument-hint: [files]\n---\nProject instructions",
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", lambda: home_dir)

    skills = load_skills(workspace_root)

    assert len(skills) == 1
    assert skills[0].command_name == "reviewer"
    assert skills[0].description == "Project skill"
    assert skills[0].argument_hint == "[files]"
    assert skills[0].source_scope == "project"
