from __future__ import annotations

from pathlib import Path
from typing import Any
import webbrowser

from claude_code_py.app.container import AppContainer
from claude_code_py.application.task_service import TaskService
from claude_code_py.providers.storage import RuntimeStateStore
from claude_code_py.skills.parser import SkillDefinition
from claude_code_py.tools.base import ToolContext, ToolExecutionError
from claude_code_py.tools.registry import ToolRegistry


def open_url(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def get_task_service(context: ToolContext) -> TaskService:
    service = context.metadata.get("task_service")
    if not isinstance(service, TaskService):
        raise ToolExecutionError("Task service is not configured.")
    return service


def get_runtime_state_store(context: ToolContext) -> RuntimeStateStore | None:
    store = context.metadata.get("runtime_state_store")
    return store if isinstance(store, RuntimeStateStore) else None


def get_app_container(context: ToolContext) -> AppContainer | None:
    container = context.metadata.get("app_container")
    return container if isinstance(container, AppContainer) else None


def get_tool_registry(context: ToolContext) -> ToolRegistry | None:
    registry = context.metadata.get("tool_registry")
    return registry if isinstance(registry, ToolRegistry) else None


def get_loaded_skills(context: ToolContext) -> list[SkillDefinition]:
    skills = context.metadata.get("loaded_skills")
    if not isinstance(skills, list):
        return []
    return [skill for skill in skills if isinstance(skill, SkillDefinition)]


def get_shared_state_bucket(context: ToolContext, key: str) -> dict[str, Any]:
    bucket = context.metadata.get(key)
    if isinstance(bucket, dict):
        return bucket
    bucket = {}
    context.metadata[key] = bucket
    return bucket


def relativize_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)
