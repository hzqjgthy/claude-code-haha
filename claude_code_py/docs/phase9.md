# 阶段九完成项

阶段九的目标是把 skills 和 commands 的外部扩展能力正式化，并先从本地目录插件开始。

本阶段已完成：

- `providers/plugins/manifest.py`
- `providers/plugins/loader.py`
- 本地目录插件扫描
- 插件 manifest 加载
- 插件提供的 commands 目录加载
- 插件提供的 skills 目录加载
- `--plugin-dir` CLI 参数
- REPL 中接入插件 commands 与插件 skills

当前行为说明：

- 默认扫描插件目录：
  - `~/.claude/plugins`
  - `<workspace>/.claude/plugins`
- 也支持临时挂载：
  - `--plugin-dir /path/to/plugin`
- 插件 manifest 当前支持：
  - `.claude-plugin/plugin.json`
  - `plugin.json`
- 如果没有 manifest，会退回到目录名作为插件名，并自动探测：
  - `commands/`
  - `skills/`
- 插件 commands 当前采用 markdown prompt command 方式接入
- 插件 skills 会并入当前 skills 加载链路

推荐的最小插件结构：

```text
my-plugin/
├─ .claude-plugin/
│  └─ plugin.json
├─ commands/
│  └─ hello.md
└─ skills/
   └─ reviewer.md
```

这版实现仍然保持边界：

- 先不做 marketplace
- 先不做插件 hooks 执行
- 先不做插件 agents 加载
- 先不做插件 MCP 服务器注入

下一阶段重点会转向多 Agent 与后台任务。
