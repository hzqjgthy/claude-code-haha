from contextlib import contextmanager
from collections.abc import Iterator

from claude_code_py.app.bootstrap import create_container
from claude_code_py.app.container import AppContainer


@contextmanager
def app_lifecycle() -> Iterator[AppContainer]:
    container = create_container()
    container.logger.debug("Application lifecycle started")
    try:
        yield container
    finally:
        container.logger.debug("Application lifecycle finished")
