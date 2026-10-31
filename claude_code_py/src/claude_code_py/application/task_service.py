from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from claude_code_py.application.query_service import QueryRequest, QueryResult, QueryService
from claude_code_py.domain.events import AppEvent
from claude_code_py.domain.tasks import TaskKind, TaskRecord
from claude_code_py.providers.llm.base import LLMProvider
from claude_code_py.tools.base import ToolContext


@dataclass(slots=True)
class TaskSubmission:
    task: TaskRecord
    result: QueryResult | None = None


class TaskService:
    def __init__(
        self,
        *,
        allow_background: bool = True,
        max_workers: int = 2,
    ) -> None:
        self._allow_background = allow_background
        self._executor = (
            ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="agent-task")
            if allow_background
            else None
        )
        self._provider: LLMProvider | None = None
        self._tool_service = None
        self._tool_context: ToolContext | None = None
        self._default_max_tokens: int = 4096
        self._tasks: dict[str, TaskRecord] = {}
        self._futures: dict[str, Future[QueryResult]] = {}
        self._events: list[AppEvent] = []
        self._lock = Lock()

    def configure(
        self,
        *,
        provider: LLMProvider,
        tool_service,
        tool_context: ToolContext,
        default_max_tokens: int,
    ) -> None:
        self._provider = provider
        self._tool_service = tool_service
        self._tool_context = tool_context
        self._default_max_tokens = default_max_tokens

    def submit_agent_task(
        self,
        *,
        description: str,
        prompt: str,
        history,
        model: str,
        system_prompt: str | None,
        session_id: str | None,
        background: bool = False,
        parent_task_id: str | None = None,
        kind: TaskKind = "agent",
        owner: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskSubmission:
        if self._provider is None or self._tool_service is None or self._tool_context is None:
            raise RuntimeError("TaskService is not configured.")

        task = TaskRecord(
            kind=kind,
            description=description,
            prompt=prompt,
            background=background,
            model=model,
            owner=owner,
            session_id=session_id,
            parent_task_id=parent_task_id,
            metadata=metadata or {},
        )
        if background and (not self._allow_background or self._executor is None):
            raise RuntimeError("Background tasks are unavailable in this mode.")
        self._store_task(task)
        if not background:
            result = self._run_task(
                task.task_id,
                QueryRequest(
                    prompt=prompt,
                    model=model,
                    history=list(history),
                    system_prompt=system_prompt,
                    max_tokens=self._default_max_tokens,
                ),
            )
            return TaskSubmission(task=self.get_task(task.task_id) or task, result=result)

        future = self._executor.submit(
            self._run_task,
            task.task_id,
            QueryRequest(
                prompt=prompt,
                model=model,
                history=list(history),
                system_prompt=system_prompt,
                max_tokens=self._default_max_tokens,
            ),
        )
        with self._lock:
            self._futures[task.task_id] = future
        return TaskSubmission(task=task)

    def list_tasks(self) -> list[TaskRecord]:
        with self._lock:
            tasks = list(self._tasks.values())
        return sorted(tasks, key=lambda task: task.created_at, reverse=True)

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            task = self._tasks.get(task_id)
        return task.model_copy(deep=True) if task is not None else None

    def update_task(
        self,
        task_id: str,
        **changes,
    ) -> TaskRecord:
        with self._lock:
            if task_id not in self._tasks:
                raise RuntimeError(f"Unknown task '{task_id}'.")
            current = self._tasks[task_id]
            updated = TaskRecord.model_validate(
                {
                    **current.model_dump(mode="python"),
                    **changes,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._tasks[task_id] = updated
        return updated.model_copy(deep=True)

    def cancel_task(self, task_id: str) -> TaskRecord:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise RuntimeError(f"Unknown task '{task_id}'.")
            future = self._futures.get(task_id)

        if future is not None:
            cancelled = future.cancel()
            if not cancelled:
                raise RuntimeError(
                    f"Task '{task_id}' is already running and cannot be stopped safely.",
                )
            with self._lock:
                self._futures.pop(task_id, None)

        return self.update_task(task_id, status="cancelled")

    def wait_for_task(self, task_id: str, timeout: float | None = None) -> TaskRecord:
        with self._lock:
            future = self._futures.get(task_id)
        if future is None:
            task = self.get_task(task_id)
            if task is None:
                raise RuntimeError(f"Unknown task '{task_id}'.")
            return task
        try:
            future.result(timeout=timeout)
        except TimeoutError as exc:
            raise RuntimeError(f"Timed out while waiting for task '{task_id}'.") from exc
        task = self.get_task(task_id)
        if task is None:
            raise RuntimeError(f"Unknown task '{task_id}'.")
        return task

    def drain_events(self) -> list[AppEvent]:
        with self._lock:
            events = list(self._events)
            self._events.clear()
        return events

    def shutdown(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=False)

    def _run_task(
        self,
        task_id: str,
        request: QueryRequest,
    ) -> QueryResult:
        existing = self.get_task(task_id)
        if existing is not None and existing.status == "cancelled":
            raise RuntimeError(f"Task '{task_id}' was cancelled before execution.")
        self._update_task(task_id, status="running")
        task_context = self._clone_tool_context(task_id)
        task_context.metadata["conversation_history"] = list(request.history)
        task_context.metadata["system_prompt"] = request.system_prompt
        task_context.metadata["current_model"] = request.model
        task_context.metadata["session_id"] = (
            self.get_task(task_id).session_id if self.get_task(task_id) is not None else None
        )
        task_context.metadata["current_task_id"] = task_id
        query_service = QueryService(
            self._provider,  # type: ignore[arg-type]
            tool_service=self._tool_service,
            tool_context=task_context,
        )
        try:
            result = query_service.submit(request)
        except Exception as exc:
            current = self.get_task(task_id)
            if current is None or current.status != "cancelled":
                self._update_task(
                    task_id,
                    status="failed",
                    error_message=str(exc),
                )
            raise
        current = self.get_task(task_id)
        if current is None or current.status != "cancelled":
            self._update_task(
                task_id,
                status="completed",
                result_text=result.text,
            )
        return result

    def _clone_tool_context(self, task_id: str) -> ToolContext:
        assert self._tool_context is not None
        metadata = dict(self._tool_context.metadata)
        metadata["current_task_id"] = task_id
        metadata["current_task_kind"] = (
            self.get_task(task_id).kind if self.get_task(task_id) is not None else "agent"
        )
        return ToolContext(
            workspace_root=self._tool_context.workspace_root,
            cwd=self._tool_context.cwd,
            default_model=self._tool_context.default_model,
            llm_provider=self._tool_context.llm_provider,
            shell_provider=self._tool_context.shell_provider,
            metadata=metadata,
        )

    def _store_task(self, task: TaskRecord) -> None:
        with self._lock:
            self._tasks[task.task_id] = task

    def _update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        result_text: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with self._lock:
            current = self._tasks[task_id]
            updated = current.model_copy(
                update={
                    "status": status or current.status,
                    "updated_at": datetime.now(UTC),
                    "result_text": result_text if result_text is not None else current.result_text,
                    "error_message": (
                        error_message
                        if error_message is not None
                        else current.error_message
                    ),
                },
            )
            self._tasks[task_id] = updated
            if updated.status in {"completed", "failed"} and updated.background:
                kind = "info" if updated.status == "completed" else "error"
                summary = (
                    f"Task {updated.task_id} completed: {updated.description}"
                    if updated.status == "completed"
                    else f"Task {updated.task_id} failed: {updated.description}"
                )
                self._events.append(AppEvent(kind=kind, message=summary))
                self._futures.pop(task_id, None)
