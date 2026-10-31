from typer.testing import CliRunner

from claude_code_py.cli.main import app


def test_cli_print_mode_routes_to_headless(monkeypatch) -> None:
    runner = CliRunner()

    def fake_run_print_mode(container, params, *, stdin, provider=None):
        del container, provider
        assert params.prompt == "hello"
        assert stdin is not None
        return 0, "mocked-response"

    monkeypatch.setattr(
        "claude_code_py.cli.main.run_print_mode",
        fake_run_print_mode,
    )

    result = runner.invoke(app, ["-p", "hello"])

    assert result.exit_code == 0
    assert "mocked-response" in result.output


def test_cli_without_print_mode_returns_guidance() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["hello"])

    assert result.exit_code == 1
    assert "interactive mode is not implemented yet" in result.output


def test_cli_permission_flags_route_to_print_mode(monkeypatch) -> None:
    runner = CliRunner()

    def fake_run_print_mode(container, params, *, stdin, provider=None):
        del container, stdin, provider
        assert params.permission_mode == "accept_edits"
        assert params.allow_rules == ["Read"]
        assert params.deny_rules == ["Write"]
        assert params.ask_rules == ["WebFetch(domain:github.com)"]
        return 0, "ok"

    monkeypatch.setattr(
        "claude_code_py.cli.main.run_print_mode",
        fake_run_print_mode,
    )

    result = runner.invoke(
        app,
        [
            "-p",
            "--permission-mode",
            "accept_edits",
            "--allow-tool",
            "Read",
            "--deny-tool",
            "Write",
            "--ask-tool",
            "WebFetch(domain:github.com)",
            "hello",
        ],
    )

    assert result.exit_code == 0


def test_cli_supports_original_permission_aliases(monkeypatch) -> None:
    runner = CliRunner()

    def fake_run_print_mode(container, params, *, stdin, provider=None):
        del container, stdin, provider
        assert params.permission_mode == "accept_edits"
        assert params.allow_rules == ["Read"]
        assert params.deny_rules == ["Write"]
        return 0, "ok"

    monkeypatch.setattr(
        "claude_code_py.cli.main.run_print_mode",
        fake_run_print_mode,
    )

    result = runner.invoke(
        app,
        [
            "-p",
            "--permission-mode",
            "acceptEdits",
            "--allowed-tools",
            "Read",
            "--disallowed-tools",
            "Write",
            "hello",
        ],
    )

    assert result.exit_code == 0


def test_cli_resume_flags_route_to_print_mode(monkeypatch) -> None:
    runner = CliRunner()

    def fake_run_print_mode(container, params, *, stdin, provider=None):
        del container, stdin, provider
        assert params.resume_session_id == "sess-1"
        assert params.continue_session is True
        assert params.fork_session is True
        return 0, "ok"

    monkeypatch.setattr(
        "claude_code_py.cli.main.run_print_mode",
        fake_run_print_mode,
    )

    result = runner.invoke(
        app,
        ["-p", "--resume", "sess-1", "--continue", "--fork-session", "hello"],
    )

    assert result.exit_code == 0


def test_cli_mcp_config_routes_to_print_mode(monkeypatch) -> None:
    runner = CliRunner()

    def fake_run_print_mode(container, params, *, stdin, provider=None):
        del container, stdin, provider
        assert params.mcp_configs == ['{"mcpServers":{}}']
        return 0, "ok"

    monkeypatch.setattr(
        "claude_code_py.cli.main.run_print_mode",
        fake_run_print_mode,
    )

    result = runner.invoke(
        app,
        ["-p", "--mcp-config", '{"mcpServers":{}}', "hello"],
    )

    assert result.exit_code == 0


def test_cli_plugin_dir_routes_to_print_mode(monkeypatch) -> None:
    runner = CliRunner()

    def fake_run_print_mode(container, params, *, stdin, provider=None):
        del container, stdin, provider
        assert params.plugin_dirs == ["/tmp/demo-plugin"]
        return 0, "ok"

    monkeypatch.setattr(
        "claude_code_py.cli.main.run_print_mode",
        fake_run_print_mode,
    )

    result = runner.invoke(
        app,
        ["-p", "--plugin-dir", "/tmp/demo-plugin", "hello"],
    )

    assert result.exit_code == 0
