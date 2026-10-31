from tests.helpers import make_tool_context

from claude_code_py.application.query_service import QueryRequest, QueryService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.tools import ToolCall
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.tools import build_default_tool_registry


class LongToolLoopProvider(LLMProvider):
    def __init__(self, rounds: int) -> None:
        self.rounds = rounds
        self.calls = 0

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.calls += 1
        if self.calls <= self.rounds:
            step = self.calls
            return CompletionResponse(
                model=request.model,
                stop_reason="tool_use",
                tool_calls=[
                    ToolCall(
                        tool_use_id=f"toolu_{step}",
                        tool_name="Write",
                        arguments={
                            "file_path": f"stress/step_{step:02d}.txt",
                            "content": f"step={step}",
                        },
                    )
                ],
                raw_response={"phase": step},
            )
        return CompletionResponse(
            model=request.model,
            text=f"completed {self.rounds} tool rounds",
            raw_response={"phase": "done"},
        )


def test_query_service_handles_long_tool_loop(tmp_path) -> None:
    rounds = 18
    provider = LongToolLoopProvider(rounds=rounds)
    context = make_tool_context(tmp_path)
    service = QueryService(
        provider,
        tool_service=ToolService(build_default_tool_registry()),
        tool_context=context,
    )

    result = service.submit(
        QueryRequest(
            prompt="run long stress loop",
            model="stress-model",
        ),
    )

    assert provider.calls == rounds + 1
    assert result.text == f"completed {rounds} tool rounds"
    for step in range(1, rounds + 1):
        assert (context.workspace_root / f"stress/step_{step:02d}.txt").exists()
