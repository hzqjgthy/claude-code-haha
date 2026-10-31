from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PluginSourceScope = Literal["user", "project", "cli_arg"]


class PluginManifest(BaseModel):
    name: str
    version: str | None = None
    description: str | None = None
    commands: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    hooks: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)

    @field_validator("commands", "skills", "hooks", "agents", mode="before")
    @classmethod
    def _coerce_string_or_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value


class LoadedPlugin(BaseModel):
    name: str
    root_path: Path
    source_scope: PluginSourceScope
    manifest: PluginManifest
    command_paths: list[Path] = Field(default_factory=list)
    skill_paths: list[Path] = Field(default_factory=list)
