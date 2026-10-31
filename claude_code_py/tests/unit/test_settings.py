from claude_code_py.app.settings import AppSettings


def test_settings_have_safe_defaults() -> None:
    settings = AppSettings()

    assert settings.app_name == "claude-code-py"
    assert settings.default_model
    assert settings.data_dir.name == "state"
