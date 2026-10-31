from __future__ import annotations

from html import unescape
import re
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from claude_code_py.domain.permissions import PermissionTarget
from claude_code_py.domain.tools import ToolExecutionResult
from claude_code_py.tools.base import BaseTool, ToolContext, ToolExecutionError

SEARCH_URL = "https://duckduckgo.com/html/"
RESULT_LIMIT = 8


class WebSearchToolInput(BaseModel):
    query: str
    allowed_domains: list[str] | None = None
    blocked_domains: list[str] | None = None


class WebSearchTool(BaseTool[WebSearchToolInput]):
    name = "WebSearch"
    description = "Search the web for current information."
    input_model = WebSearchToolInput
    read_only = True
    destructive = False

    def validate(self, payload: WebSearchToolInput, context: ToolContext) -> None:
        del context
        if len(payload.query.strip()) < 2:
            raise ToolExecutionError("query must contain at least 2 characters.")

    def summarize(self, payload: WebSearchToolInput) -> str:
        return payload.query

    def permission_targets(
        self,
        payload: WebSearchToolInput,
        context: ToolContext,
    ) -> list[PermissionTarget]:
        del payload, context
        return [PermissionTarget(tool_name=self.name)]

    def execute(self, payload: WebSearchToolInput, context: ToolContext) -> ToolExecutionResult:
        del context
        response = httpx.get(
            SEARCH_URL,
            params={"q": payload.query},
            headers={"user-agent": "claude-code-py/0.1"},
            follow_redirects=True,
            timeout=20.0,
        )
        response.raise_for_status()
        results = _extract_search_results(response.text)
        filtered = []
        for result in results:
            hostname = urlparse(result["url"]).netloc.lower()
            if payload.allowed_domains and not any(
                hostname.endswith(domain.lower()) for domain in payload.allowed_domains
            ):
                continue
            if payload.blocked_domains and any(
                hostname.endswith(domain.lower()) for domain in payload.blocked_domains
            ):
                continue
            filtered.append(result)
            if len(filtered) >= RESULT_LIMIT:
                break
        if not filtered:
            output = "No search results found"
        else:
            lines = [f"Search results for: {payload.query}"]
            lines.extend(
                f"- {item['title']} | {item['url']}"
                for item in filtered
            )
            output = "\n".join(lines)
        return ToolExecutionResult(
            tool_name=self.name,
            tool_use_id=None,
            output=output,
            structured_output={
                "query": payload.query,
                "results": filtered,
                "result_count": len(filtered),
            },
        )


def _extract_search_results(html: str) -> list[dict[str, str]]:
    matches = re.findall(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    results: list[dict[str, str]] = []
    for url, title in matches:
        clean_title = re.sub(r"<[^>]+>", "", title)
        clean_url = unescape(url)
        if not clean_url.startswith("http"):
            continue
        results.append(
            {
                "title": unescape(clean_title).strip(),
                "url": clean_url.strip(),
            }
        )
    return results
