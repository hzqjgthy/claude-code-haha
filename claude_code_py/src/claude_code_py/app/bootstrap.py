from claude_code_py.app.container import AppContainer
from claude_code_py.app.settings import AppSettings
from claude_code_py.common.logging import configure_logging, get_logger
from claude_code_py.common.paths import build_project_paths


def create_container() -> AppContainer:
    settings = AppSettings()
    paths = build_project_paths()
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.sessions_dir.mkdir(parents=True, exist_ok=True)
    paths.session_index_path.parent.mkdir(parents=True, exist_ok=True)
    configure_logging(settings.log_level)
    logger = get_logger("claude_code_py")
    logger.debug("Container created")
    return AppContainer(settings=settings, paths=paths, logger=logger)
