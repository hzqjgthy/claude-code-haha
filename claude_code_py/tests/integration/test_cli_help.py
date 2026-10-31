from typer.testing import CliRunner

from claude_code_py.cli.main import app


def test_cli_help_renders() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Independent Python rewrite skeleton" in result.output


def test_cli_doctor_renders_basic_state() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "app_name=claude-code-py" in result.output


def test_cli_sessions_routes_to_builtin(monkeypatch) -> None:
    runner = CliRunner()

    def fake_sessions_command(limit: int = 20) -> None:
        assert limit == 5

    monkeypatch.setattr(
        "claude_code_py.cli.main.sessions_command",
        fake_sessions_command,
    )

    result = runner.invoke(app, ["sessions", "5"])

    assert result.exit_code == 0
