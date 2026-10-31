from __future__ import annotations

from claude_code_py.commands.loader import CommandContext
from claude_code_py.common.env_files import update_env_file


def auth_status_lines(context: CommandContext) -> list[str]:
    settings = context.container.settings
    mode = "none"
    if settings.anthropic_api_key:
        mode = "api_key"
    elif settings.anthropic_auth_token:
        mode = "auth_token"
    return [
        "Auth status:",
        f"mode: {mode}",
        (
            f"api_key_configured: {'yes' if settings.anthropic_api_key else 'no'}"
        ),
        (
            "auth_token_configured: "
            f"{'yes' if settings.anthropic_auth_token else 'no'}"
        ),
        f"env_file: {context.container.paths.env_file}",
    ]


def set_api_key(context: CommandContext, value: str) -> None:
    normalized = value.strip()
    update_env_file(
        context.container.paths.env_file,
        {
            "ANTHROPIC_API_KEY": normalized,
            "ANTHROPIC_AUTH_TOKEN": None,
        },
    )
    context.container.settings.anthropic_api_key = normalized
    context.container.settings.anthropic_auth_token = None
    _apply_provider_credentials(context, api_key=normalized, auth_token=None)


def set_auth_token(context: CommandContext, value: str) -> None:
    normalized = value.strip()
    update_env_file(
        context.container.paths.env_file,
        {
            "ANTHROPIC_AUTH_TOKEN": normalized,
            "ANTHROPIC_API_KEY": None,
        },
    )
    context.container.settings.anthropic_auth_token = normalized
    context.container.settings.anthropic_api_key = None
    _apply_provider_credentials(context, api_key=None, auth_token=normalized)


def clear_auth(context: CommandContext) -> None:
    update_env_file(
        context.container.paths.env_file,
        {
            "ANTHROPIC_API_KEY": None,
            "ANTHROPIC_AUTH_TOKEN": None,
        },
    )
    context.container.settings.anthropic_api_key = None
    context.container.settings.anthropic_auth_token = None
    _apply_provider_credentials(context, api_key=None, auth_token=None)


def _apply_provider_credentials(
    context: CommandContext,
    *,
    api_key: str | None,
    auth_token: str | None,
) -> None:
    provider = context.tool_context.llm_provider
    if provider is None:
        return
    if hasattr(provider, "_api_key"):
        setattr(provider, "_api_key", api_key)
    if hasattr(provider, "_auth_token"):
        setattr(provider, "_auth_token", auth_token)
