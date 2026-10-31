# 阶段八完成项

阶段八的目标是给 Python 重构版恢复第一版 MCP 能力，并保持与原项目相同的分层方向：配置加载、客户端连接、工具适配。

本阶段已完成：

- `providers/mcp/base.py`
- `providers/mcp/config_loader.py`
- `providers/mcp/client.py`
- `tools/mcp.py`
- `--mcp-config` CLI 参数
- `.mcp.json` 项目级配置加载
- stdio MCP server 连接
- HTTP MCP server 连接
- MCP tools 动态注册到现有 ToolRegistry
- REPL 与 print 模式都可使用 MCP tools

当前行为说明：

- 当前支持：
  - `stdio`
  - `http`
- 当前配置来源支持：
  - `<workspace>/.mcp.json`
  - `--mcp-config`
- `--mcp-config` 支持：
  - JSON 文件路径
  - JSON 字符串
- MCP tool 名称格式当前为：
  - `mcp__<server>__<tool>`
- print 模式 JSON 输出会附带：
  - `mcp_errors`
- REPL 启动时会把 MCP 连接/加载错误显示为 system warning

这版实现仍然保持边界：

- 先不做 SSE / WebSocket transport
- 先不做 OAuth
- 先不做 MCP resources / prompts / elicitation
- 先不做复杂的 MCP 命令生态

下一阶段重点会转向插件系统。
