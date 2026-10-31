from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / ".local" / "state"


def _default_env_file() -> Path:
    return Path(__file__).resolve().parents[3] / ".env"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_default_env_file()),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "claude-code-py"
    debug: bool = Field(default=False, alias="CLAUDE_CODE_PY_DEBUG")
    log_level: str = Field(default="INFO", alias="CLAUDE_CODE_PY_LOG_LEVEL")
    default_model: str = Field(
        default="claude-sonnet-4-5",
        alias="CLAUDE_CODE_PY_DEFAULT_MODEL",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CLAUDE_CODE_PY_ANTHROPIC_API_KEY",
            "ANTHROPIC_API_KEY",
        ),
    )
    anthropic_auth_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CLAUDE_CODE_PY_ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_AUTH_TOKEN",
        ),
    )
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com",
        validation_alias=AliasChoices(
            "CLAUDE_CODE_PY_ANTHROPIC_BASE_URL",
            "ANTHROPIC_BASE_URL",
        ),
    )
    api_timeout_ms: int = Field(
        default=600_000,
        validation_alias=AliasChoices(
            "CLAUDE_CODE_PY_API_TIMEOUT_MS",
            "API_TIMEOUT_MS",
        ),
    )
    default_max_tokens: int = 4096
    data_dir: Path = Field(default_factory=_default_data_dir)
