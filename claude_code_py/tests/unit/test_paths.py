from claude_code_py.common.paths import build_project_paths


def test_project_paths_stay_inside_project_root() -> None:
    paths = build_project_paths()

    assert paths.root.name == "claude_code_py"
    assert paths.package_root.name == "claude_code_py"
    assert paths.env_file.parent == paths.root
