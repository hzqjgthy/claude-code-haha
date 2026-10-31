import logging
from pathlib import Path
from types import SimpleNamespace

from claude_code_py.app.container import AppContainer
from claude_code_py.common.paths import ProjectPaths
from claude_code_py.providers.llm.base import LLMProvider
from claude_code_py.providers.shell import SubprocessShellProvider
from claude_code_py.tools.base import ToolContext


def make_test_container(tmp_path: Path) -> AppContainer:
    root = tmp_path / "project"
    paths = ProjectPaths(
        root=root,
        src_root=root / "src",
        package_root=root / "src" / "claude_code_py",
        docs_dir=root / "docs",
        tests_dir=root / "tests",
        scripts_dir=root / "scripts",
        data_dir=root / ".local" / "state",
        sessions_dir=root / ".local" / "state" / "sessions",
        session_index_path=root / ".local" / "state" / "session_index.sqlite3",
        env_file=root / ".env",
    )
    paths.sessions_dir.mkdir(parents=True, exist_ok=True)
    settings = SimpleNamespace(
        app_name="claude-code-py",
        debug=False,
        log_level="INFO",
        default_model="test-model",
        anthropic_api_key=None,
        anthropic_auth_token=None,
        anthropic_base_url="https://api.anthropic.com",
        api_timeout_ms=600_000,
        default_max_tokens=4096,
        data_dir=paths.data_dir,
    )
    return AppContainer(
        settings=settings,
        paths=paths,
        logger=logging.getLogger("test"),
    )


def make_tool_context(
    tmp_path: Path,
    *,
    llm_provider: LLMProvider | None = None,
) -> ToolContext:
    container = make_test_container(tmp_path)
    workspace_root = container.paths.root / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    return ToolContext(
        workspace_root=workspace_root,
        cwd=workspace_root,
        default_model=container.settings.default_model,
        llm_provider=llm_provider,
        shell_provider=SubprocessShellProvider(),
    )
