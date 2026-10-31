# Phase 17 - Tools Expansion

## Goal

Bring the Python rebuild from a minimal tool loop to a tool surface that is much closer to the original project's commonly used tools.

## Completed In This Phase

### Existing core tools retained

- `Bash`
- `Read`
- `Edit`
- `Write`
- `WebFetch`
- `Agent`
- MCP wrapped tools (`mcp__<server>__<tool>`)

### Newly implemented core tools

- `Glob`
- `Grep`
- `TodoWrite`
- `WebSearch`
- `PowerShell`
- `NotebookEdit`
- `Sleep`
- `Skill`

### Newly implemented task tools

- `TaskCreate`
- `TaskGet`
- `TaskList`
- `TaskOutput`
- `TaskStop`
- `TaskUpdate`

### Newly implemented coordination tools

- `TeamCreate`
- `TeamDelete`
- `SendMessage`

### Newly implemented MCP / discovery / config tools

- `ListMcpResourcesTool`
- `ReadMcpResourceTool`
- `McpAuth`
- `ToolSearch`
- `Config`
- `AskUserQuestion`
- `workflow`

## Supporting Runtime Changes

- Expanded the default tool registry so the new tools are exposed to the model.
- Added lazy imports in `tools/__init__.py` to avoid circular-import breakage while growing the tool surface.
- Extended `TaskService` with:
  - task updates
  - task cancellation for cancellable background work
  - cancellation-aware completion handling
- Extended the MCP client layer with:
  - resource listing
  - resource reading
- Attached more runtime metadata into `ToolContext` so tools can access:
  - runtime preferences
  - app container
  - MCP manager
  - loaded skills
  - tool registry
- Added a REPL-side `AskUserQuestion` callback path so the tool can work in interactive prompt mode.

## Validation

This phase is covered by:

- existing unit/integration/parity/stress tests
- new unit coverage for:
  - `Glob`
  - `Grep`
  - `TodoWrite`
  - `NotebookEdit`
  - `TaskCreate/List/Output`
  - `Skill`
  - `WebSearch`
  - `Config`
  - `ToolSearch`
  - expanded tool registry surface

Validation commands:

```bash
pytest -q
python scripts/release_check.py
```

## Parity Notes

This phase closes the biggest "tool surface too thin" gap from the comparison report.

Some tools are now present with a lightweight Python-native implementation first, while deeper product parity is intentionally deferred to later phases:

- `AskUserQuestion`
  - REPL callback path is implemented.
  - richer Textual interactive flow can be deepened later.
- `TeamCreate` / `TeamDelete` / `SendMessage`
  - lightweight in-memory coordination layer is implemented now.
  - deeper multi-agent product parity belongs with later agent/task/remote phases.
- `McpAuth`
  - tool surface is present.
  - fully automated OAuth/product flow remains a later MCP/remote deepening task.

## Outcome

The Python project is no longer restricted to just file read/write/edit and shell/web fetch.

With this phase complete, the rebuild can support much more of the original project's real-world tool-driven workflows, and later phases can focus on:

- permissions and sandbox depth
- long-session durability
- MCP/plugin/agent deepening
- remote / bridge parity
