from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from claude_code_py.application.query_service import QueryRequest, QueryService
from claude_code_py.application.tool_service import ToolService
from claude_code_py.domain.tools import ToolCall
from claude_code_py.providers.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
)
from claude_code_py.providers.shell import SubprocessShellProvider
from claude_code_py.tools import build_default_tool_registry
from claude_code_py.tools.base import ToolContext


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


def build_context(workspace_root: Path) -> ToolContext:
    return ToolContext(
        workspace_root=workspace_root,
        cwd=workspace_root,
        default_model="stress-model",
        shell_provider=SubprocessShellProvider(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a long local tool-loop stress test."
    )
    parser.add_argument("--rounds", type=int, default=25, help="Number of tool rounds.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="claude-code-py-stress-") as temp_dir:
        workspace_root = Path(temp_dir)
        provider = LongToolLoopProvider(rounds=args.rounds)
        context = build_context(workspace_root)
        service = QueryService(
            provider,
            tool_service=ToolService(build_default_tool_registry()),
            tool_context=context,
        )
        result = service.submit(
            QueryRequest(prompt="run stress loop", model="stress-model"),
        )

        created = sorted(
            path.relative_to(workspace_root) for path in workspace_root.rglob("*.txt")
        )
        print(f"tool_rounds={args.rounds}")
        print(f"provider_calls={provider.calls}")
        print(f"result={result.text}")
        print(f"created_files={len(created)}")
        for path in created[:5]:
            print(f"sample={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
