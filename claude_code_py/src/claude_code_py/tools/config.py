from __future__ import annotations

from pydantic import BaseModel

from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools._helpers import get_runtime_state_store
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError


class ConfigToolInput(BaseModel):
    setting: str
    value: str | bool | int | float | None = None


class ConfigTool(BaseTool[ConfigToolInput]):
    name = "Config"
    description = "Get or set supported Claude Code Python settings."
    input_model = ConfigToolInput
    read_only = False
    destructive = False

    def summarize(self, payload: ConfigToolInput) -> str:
        return payload.setting

    def execute(self, payload: ConfigToolInput, context: ToolContext) -> ToolExecutionResult:
        setting = payload.setting.strip()
        if not setting:
            raise ToolExecutionError("setting cannot be empty.")

        if payload.value is None:
            value = _read_setting(setting, context)
            return ToolExecutionResult(
                tool_name=self.name,
                tool_use_id=None,
                output=f"{setting} = {value}",
                structured_output={
                    "success": True,
                    "operation": "get",
                    "setting": setting,
                    "value": value,
                },
            )

        previous_value = _read_setting(setting, context)
        _write_setting(setting, payload.value, context)
        new_value = _read_setting(setting, context)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=f"{setting} updated from {previous_value} to {new_value}",
            structured_output={
                "success": True,
                "operation": "set",
                "setting": setting,
                "previousValue": previous_value,
                "newValue": new_value,
            },
        )


def _read_setting(setting: str, context: ToolContext):
    if setting == "model":
        return context.metadata.get("current_model", context.default_model)
    store = get_runtime_state_store(context)
    if store is None:
        raise ToolExecutionError("Runtime settings are not configured.")
    prefs = store.get_preferences()
    if not hasattr(prefs, setting):
        raise ToolExecutionError(f'Unknown setting: "{setting}"')
    return getattr(prefs, setting)


def _write_setting(setting: str, value, context: ToolContext) -> None:
    if setting == "model":
        context.metadata["current_model"] = str(value)
        return
    store = get_runtime_state_store(context)
    if store is None:
        raise ToolExecutionError("Runtime settings are not configured.")
    prefs = store.get_preferences()
    if not hasattr(prefs, setting):
        raise ToolExecutionError(f'Unknown setting: "{setting}"')
    store.update_preferences(**{setting: value})
