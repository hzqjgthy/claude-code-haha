from claude_code_py.app.container import AppContainer
from claude_code_py.cli.repl_mode import ReplModeParams
from claude_code_py.providers.llm.base import LLMProvider
from claude_code_py.providers.remote import RemoteProvider


def _load_textual_app_class():
    try:
        from claude_code_py.ui.textual.app import ClaudeCodeTextualApp
    except ModuleNotFoundError as exc:
        if exc.name is not None and exc.name.startswith("textual"):
            raise RuntimeError(
                "Textual UI requires the 'textual' package. "
                'Reinstall the project or run `pip install -e ".[dev]"` again.',
            ) from exc
        raise
    return ClaudeCodeTextualApp


def run_textual_mode(
    container: AppContainer,
    params: ReplModeParams,
    *,
    provider: LLMProvider | None = None,
    remote_provider: RemoteProvider | None = None,
) -> int:
    app_class = _load_textual_app_class()
    try:
        app = app_class(
            container,
            params,
            provider=provider,
            remote_provider=remote_provider,
        )
    except (RuntimeError, ValueError) as exc:
        raise RuntimeError(str(exc)) from exc

    try:
        result = app.run()
    finally:
        app.shutdown_runtime()
    return result if isinstance(result, int) else 0
