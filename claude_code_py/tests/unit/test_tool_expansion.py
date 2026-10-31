import json
from pathlib import Path

from claude_code_py.application.task_service import TaskService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.tools import ToolExecutionRequest
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.providers.storage import RuntimeStateStore
from claude_code_py.tools import build_default_tool_registry
from tests.helpers import make_test_container, make_tool_context


class FakeProvider(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        prompt = request.messages[-1].content  # type: ignore[union-attr]
        return CompletionResponse(
            model=request.model,
            text=f"assistant:{prompt}",
            raw_response={"model": request.model},
        )


def test_glob_and_grep_tools_find_workspace_files(tmp_path) -> None:
    service = ToolService(build_default_tool_registry())
    context = make_tool_context(tmp_path)
    root = context.workspace_root
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "main.py").write_text("print('hello')\nvalue = 1\n", encoding="utf-8")
    (root / "src" / "other.txt").write_text("hello world\n", encoding="utf-8")

    glob_result = service.execute(
        ToolExecutionRequest(
            tool_name="Glob",
            arguments={"pattern": "src/**/*.py"},
        ),
        context,
    )
    grep_result = service.execute(
        ToolExecutionRequest(
            tool_name="Grep",
            arguments={"pattern": "hello", "path": "src", "output_mode": "files_with_matches"},
        ),
        context,
    )

    assert "src/main.py" in glob_result.result.output
    assert "src/main.py" in grep_result.result.output
    assert "src/other.txt" in grep_result.result.output


def test_todo_write_and_notebook_edit_tools_work(tmp_path) -> None:
    service = ToolService(build_default_tool_registry())
    context = make_tool_context(tmp_path)
    context.metadata["session_id"] = "sess-1"

    todo_result = service.execute(
        ToolExecutionRequest(
            tool_name="TodoWrite",
            arguments={
                "todos": [
                    {"content": "Inspect repo", "status": "pending"},
                    {"content": "Write tests", "status": "in_progress"},
                ]
            },
        ),
        context,
    )
    assert "Active items: 2" in todo_result.result.output
    assert len(todo_result.result.structured_output["newTodos"]) == 2

    notebook = context.workspace_root / "demo.ipynb"
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "id": "cell-1",
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": ["old\n"],
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
    edit_result = service.execute(
        ToolExecutionRequest(
            tool_name="NotebookEdit",
            arguments={
                "notebook_path": str(notebook),
                "cell_id": "cell-1",
                "new_source": "updated",
                "edit_mode": "replace",
            },
        ),
        context,
    )
    assert "Updated cell cell-1" == edit_result.result.output
    updated = json.loads(notebook.read_text(encoding="utf-8"))
    assert updated["cells"][0]["source"] == ["updated"]


def test_task_and_skill_tools_integrate_with_runtime_services(tmp_path) -> None:
    provider = FakeProvider()
    context = make_tool_context(tmp_path, llm_provider=provider)
    registry = build_default_tool_registry()
    tool_service = ToolService(registry)
    task_service = TaskService(allow_background=True)
    task_service.configure(
        provider=provider,
        tool_service=tool_service,
        tool_context=context,
        default_max_tokens=256,
    )
    context.metadata["task_service"] = task_service
    context.metadata["tool_registry"] = registry
    context.metadata["session_id"] = "sess-1"
    context.metadata["current_model"] = "test-model"

    skill_dir = context.workspace_root / ".claude" / "skills" / "reviewer"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        (
            "---\n"
            "name: Reviewer\n"
            "description: Review changes\n"
            "---\n"
            "Focus on regressions."
        ),
        encoding="utf-8",
    )
    context.metadata["loaded_skills"] = []

    task_result = tool_service.execute(
        ToolExecutionRequest(
            tool_name="TaskCreate",
            arguments={
                "description": "background review",
                "prompt": "review auth",
                "background": True,
            },
        ),
        context,
    )
    task_id = task_result.result.structured_output["task"]["task_id"]
    listed = tool_service.execute(
        ToolExecutionRequest(tool_name="TaskList", arguments={}),
        context,
    )
    output = tool_service.execute(
        ToolExecutionRequest(
            tool_name="TaskOutput",
            arguments={"task_id": task_id, "block": True, "timeout_ms": 2000},
        ),
        context,
    )
    skill_result = tool_service.execute(
        ToolExecutionRequest(
            tool_name="Skill",
            arguments={"skill_name": "reviewer", "arguments": "auth module"},
        ),
        context,
    )

    assert task_id in listed.result.output
    assert "assistant:review auth" in output.result.output
    assert "assistant:auth module" in skill_result.result.output


def test_web_search_config_and_tool_search_tools(tmp_path, monkeypatch) -> None:
    provider = FakeProvider()
    context = make_tool_context(tmp_path, llm_provider=provider)
    container = make_test_container(tmp_path)
    store = RuntimeStateStore(container.paths.data_dir / "runtime_state.json")
    registry = build_default_tool_registry()
    service = ToolService(registry)
    context.metadata["runtime_state_store"] = store
    context.metadata["tool_registry"] = registry

    class FakeResponse:
        status_code = 200
        text = """
        <a class=\"result__a\" href=\"https://example.com/article\">Example Result</a>
        <a class=\"result__a\" href=\"https://python.org/doc\">Python Docs</a>
        """

        def raise_for_status(self):
            return None

    monkeypatch.setattr("claude_code_py.tools.web_search.httpx.get", lambda *a, **k: FakeResponse())

    search = service.execute(
        ToolExecutionRequest(
            tool_name="WebSearch",
            arguments={"query": "python", "allowed_domains": ["python.org"]},
        ),
        context,
    )
    set_config = service.execute(
        ToolExecutionRequest(
            tool_name="Config",
            arguments={"setting": "theme", "value": "light"},
        ),
        context,
    )
    find_tool = service.execute(
        ToolExecutionRequest(
            tool_name="ToolSearch",
            arguments={"query": "notebook", "max_results": 3},
        ),
        context,
    )

    assert "Python Docs" in search.result.output
    assert "example.com" not in search.result.output
    assert "theme updated from" in set_config.result.output
    assert "NotebookEdit" in find_tool.result.output
