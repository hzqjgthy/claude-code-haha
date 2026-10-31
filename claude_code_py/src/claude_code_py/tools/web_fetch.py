from time import perf_counter
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from claude_code_py.domain.messages import UserMessage
from claude_code_py.domain.permissions import (
    PermissionDecision,
    PermissionPromptRequest,
    PermissionTarget,
)
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.providers.llm.base import CompletionRequest
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError
from claude_code_py.tools.permission_preview import clip_text

MAX_WEB_FETCH_CHARS = 12_000


class WebFetchToolInput(BaseModel):
    url: str
    prompt: str
    max_chars: int = Field(default=MAX_WEB_FETCH_CHARS, ge=256, le=100_000)


class WebFetchTool(BaseTool[WebFetchToolInput]):
    name = "WebFetch"
    description = "Fetch a web page and apply a natural-language prompt to its content."
    input_model = WebFetchToolInput
    read_only = True
    destructive = False

    def validate(self, payload: WebFetchToolInput, context: ToolContext) -> None:
        del context
        parsed = urlparse(payload.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ToolExecutionError(f"Invalid URL: {payload.url}")

    def summarize(self, payload: WebFetchToolInput) -> str:
        return payload.url

    def permission_targets(
        self,
        payload: WebFetchToolInput,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        del context
        parsed = urlparse(payload.url)
        hostname = parsed.netloc or payload.url
        return [
            PermissionTarget(tool_name=self.name),
            PermissionTarget(tool_name=self.name, kind="domain", value=hostname),
        ]

    def check_permissions(
        self,
        payload: WebFetchToolInput,
        context: ToolContext,
    ) -> PermissionDecision:
        del payload
        prefs = _runtime_preferences(context)
        if prefs is None or not prefs.sandbox_enabled:
            return PermissionDecision(behavior="allow")
        if prefs.sandbox_allow_unsandboxed_fallback:
            return PermissionDecision(behavior="allow")
        return PermissionDecision(
            behavior="ask",
            reason=(
                "Sandbox is enabled, but this Python refactor does not yet "
                "proxy WebFetch through an enforced network sandbox. Approval "
                "is required before issuing the request directly."
            ),
        )

    def build_permission_request(
        self,
        payload: WebFetchToolInput,
        context: ToolContext,
        *,
        summary: str,
        reason: str | None,
    ) -> PermissionPromptRequest:
        parsed = urlparse(payload.url)
        hostname = parsed.netloc or payload.url
        return PermissionPromptRequest(
            tool_name=self.name,
            summary=summary,
            reason=reason,
            targets=self.permission_targets(payload, context),
            request_kind="web_fetch",
            title="Fetch web content",
            subtitle=hostname,
            prompt="Do you want to allow Claude to fetch this URL?",
            detail_lines=[
                f"url: {payload.url}",
                f"domain: {hostname}",
                f"max_chars: {payload.max_chars}",
                f"prompt: {payload.prompt}",
            ],
            preview=clip_text(payload.prompt, max_lines=12, max_chars=1200),
            metadata={"url": payload.url, "domain": hostname},
        )

    def execute(self, payload: WebFetchToolInput, context: ToolContext) -> ToolExecutionResult:
        start = perf_counter()
        response = httpx.get(payload.url, follow_redirects=True, timeout=20.0)
        response.raise_for_status()
        fetched_text = response.text[: payload.max_chars]
        elapsed_ms = int((perf_counter() - start) * 1000)

        result_text = fetched_text
        used_llm = False
        if context.llm_provider is not None:
            llm_request = CompletionRequest(
                model=context.default_model,
                system_prompt=None,
                max_tokens=2048,
                messages=[
                    UserMessage(
                        content=(
                            "You are processing fetched web content.\n"
                            f"User request: {payload.prompt}\n\n"
                            f"Fetched content from {payload.url}:\n\n{fetched_text}"
                        ),
                    )
                ],
            )
            completion = context.llm_provider.complete(llm_request)
            result_text = completion.text
            used_llm = True

        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=result_text,
            structured_output={
                "url": str(response.url),
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "fetched_chars": len(fetched_text),
                "used_llm": used_llm,
            },
        )


def _runtime_preferences(context: ToolContext):
    store = context.metadata.get("runtime_state_store")
    if store is None:
        return None
    getter = getattr(store, "get_preferences", None)
    if not callable(getter):
        return None
    return getter()
