import httpx

from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.messages import UserMessage
from claude_code_py.domain.tools import ToolExecutionRequest
from claude_code_py.providers.llm.base import CompletionRequest, CompletionResponse, LLMProvider
from claude_code_py.tools import build_default_tool_registry
from tests.helpers import make_tool_context


class FakeProvider(LLMProvider):
    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        assert isinstance(request.messages[0], UserMessage)
        return CompletionResponse(
            model=request.model,
            text="processed web content",
            raw_response={"ok": True},
        )


def test_web_fetch_tool_uses_llm_provider(tmp_path, monkeypatch) -> None:
    def fake_get(url: str, *, follow_redirects: bool, timeout: float) -> httpx.Response:
        del follow_redirects, timeout
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, text="example page body")

    monkeypatch.setattr("claude_code_py.tools.web_fetch.httpx.get", fake_get)

    llm_provider = FakeProvider()
    context = make_tool_context(tmp_path, llm_provider=llm_provider)
    service = ToolService(build_default_tool_registry())

    envelope = service.execute(
        ToolExecutionRequest(
            tool_name="WebFetch",
            arguments={
                "url": "https://example.com",
                "prompt": "Summarize the page",
            },
        ),
        context,
    )

    assert envelope.result.is_error is False
    assert envelope.result.output == "processed web content"
    assert len(llm_provider.requests) == 1


def test_web_fetch_tool_rejects_invalid_url(tmp_path) -> None:
    context = make_tool_context(tmp_path)
    service = ToolService(build_default_tool_registry())

    envelope = service.execute(
        ToolExecutionRequest(
            tool_name="WebFetch",
            arguments={
                "url": "not-a-url",
                "prompt": "Summarize",
            },
        ),
        context,
    )

    assert envelope.result.is_error is True
