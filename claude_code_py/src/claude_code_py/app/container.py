from dataclasses import dataclass
from logging import Logger

from claude_code_py.app.settings import AppSettings
from claude_code_py.common.paths import ProjectPaths


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    paths: ProjectPaths
    logger: Logger
