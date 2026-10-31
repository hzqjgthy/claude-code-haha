from typer.testing import CliRunner

from claude_code_py.cli.main import app


def test_cli_textual_mode_routes_to_tui(monkeypatch) -> None:
    runner = CliRunner()

    def fake_run_textual_mode(
        container, params, *, provider=None, remote_provider=None
    ):
        del container, provider, remote_provider
        assert params.initial_prompt == "hello"
        assert params.session_id == "sess-1"
        return 0

    monkeypatch.setattr(
        "claude_code_py.cli.main.run_textual_mode",
        fake_run_textual_mode,
    )
    monkeypatch.setattr(
        "claude_code_py.cli.main._stdin_is_tty",
        lambda: True,
    )

    result = runner.invoke(app, ["--textual", "--session-id", "sess-1", "hello"])

    assert result.exit_code == 0


def test_cli_rejects_print_and_textual_together() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--textual", "-p", "hello"])

    assert result.exit_code == 1
    assert "--print and --textual cannot be combined" in result.output
