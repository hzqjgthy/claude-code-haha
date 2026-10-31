# claude_code_py

`claude_code_py` 是当前仓库内完全隔离的 Python 独立项目骨架。

它遵守以下约束：

- 全部实现都在 `claude_code_py/` 内
- 不能依赖外层 TypeScript 项目的代码、脚本、配置和资源
- 未来可以把整个目录直接剪切出去，作为单独项目运行

## 当前状态

当前完成的是“阶段一：Python 项目骨架”：

- `conda` 环境定义
- `pyproject.toml` 与可编辑安装
- 最小 CLI 入口
- 基础 app/common/domain 分层
- 基础测试与代码质量配置

当前还包含“阶段二的最小 headless 链路”：

- `-p/--print`
- `--model`
- `--system-prompt`
- `--system-prompt-file`
- `--append-system-prompt`
- `--output-format text|json`
- `--session-id`
- stdin 管道输入

当前还包含“阶段三的基础工具系统”：

- Tool 协议
- Tool Registry
- Tool Service
- `tool_use / tool_result`
- 核心工具：
  - `Bash`
  - `Read`
  - `Edit`
  - `Write`
- `WebFetch`
- 最小 tool-use loop

当前还包含“阶段四的基础权限系统”：

- `PermissionRule / PermissionContext / PermissionDecision`
- `PermissionService`
- `PermissionEngine`
- 规则来源：
  - session
  - user settings
  - project settings
  - CLI args
- 规则行为：
  - allow
  - deny
  - ask
- headless `--print` 路径下的统一权限前置检查

当前还包含“阶段五的会话持久化与恢复”：

- JSONL transcript 持久化
- SQLite session index
- 最近会话列表
- `--resume`
- `--continue`
- `--fork-session`
- 缺失索引的 transcript 自动回填

当前还包含“阶段六的交互式 REPL”：

- 默认进入交互模式
- `prompt_toolkit` 驱动
- 多轮对话
- 输入历史
- 多行输入
- `Esc+Enter` 提交
- `Ctrl+D` 退出

当前还包含“阶段七的 Commands 与 Skills”：

- slash command 解析与注册
- 内置命令：
  - `/help`
  - `/resume`
  - `/clear`
  - `/model`
  - `/review`
  - `/skills`
  - `/status`
  - `/doctor`
  - `/config`
  - `/context`
  - `/export`
  - `/plan`
  - `/permissions`
  - `/plugin`
  - `/mcp`
  - `/files`
  - `/diff`
  - `/hooks`
  - `/memory`
  - `/rename`
  - `/rewind`
  - `/session`
- markdown skills 加载
- frontmatter 解析
- REPL 中可调用 `user-invocable: true` 的 skills

当前还包含“阶段八的 MCP 支持”：

- MCP config loader
- stdio / HTTP MCP client
- `.mcp.json`
- `--mcp-config`
- MCP tools 动态注册
- REPL / print 路径下的 MCP tool 调用

当前还包含“阶段九的插件系统”：

- 本地目录插件扫描
- 插件 manifest 加载
- 插件 commands / skills 目录加载
- `--plugin-dir`
- REPL 中插件命令与插件技能接入

当前还包含“阶段十的多 Agent 与后台任务”：

- `Agent` 工具
- 进程内子代理
- 后台任务状态管理
- `/tasks`
- REPL 中后台任务完成提示

当前还包含“阶段十一的初版 Textual TUI 壳层”：

- `--textual` / `--tui`
- Textual controller 层
- Textual state / widgets / dialogs 分层
- 初版状态栏
- 初版任务面板
- 初版消息区与输入区
- 交互式权限审批弹窗
- 会话级权限记忆
- remote status 展示
- 命令帮助 / 最新任务 / remote 信息弹窗

注意：

- 这一步只是把 Python 服务层接进了一个可运行的 Textual 壳层
- 它已经开始按原项目 `StatusLine / Messages / PromptInput / PermissionRequest / TaskList` 的方向拆模块
- 但它还没有完全对齐原项目 `src/screens/REPL.tsx` 那套 Ink/React 交互架构
- 后续仍需继续补齐 PromptInput 建议系统、完整任务导航、remote callout/bridge 等原项目能力

当前还包含“阶段十三的 runtime / state 骨架”：

- `ui/state`
- `ui/runtime`
- Textual app 改为消费 `store + selectors`
- 为后续 fullscreen layout、PromptInput、Messages 深化做准备

当前还包含“阶段十四的 fullscreen layout 分层”：

- `ui/layout/fullscreen.py`
- `ui/layout/modal_manager.py`
- `ui/layout/overlay_manager.py`
- Textual app 改为通过 layout 组合 transcript / tasks / overlay / modal / prompt
- 权限审批进入 overlay 区
- 信息面板进入 modal 区

当前还包含“阶段十五的 PromptInput / StatusLine / Messages 深化”：

- Prompt state / prompt suggestions
- command mode 与 slash command 建议
- richer status line
- transcript 分类渲染

当前还包含“阶段十六的第一批 Commands 扩展”：

- 新增内置命令：
  - `/status`
  - `/doctor`
  - `/config`
  - `/permissions`
  - `/plugin`
  - `/mcp`
  - `/files`
  - `/rename`
- `/permissions`
  - 支持运行时切换 permission mode
  - 支持追加 session 级 allow / deny / ask 规则
  - 支持清理 session 规则
- `/plugin`
  - 支持 list / show / reload / errors
- `/mcp`
  - 支持 list / tools / show
- `/files`
  - `Read / Edit / Write` 会自动把文件加入当前 file context
- `/rename`
  - 支持直接修改当前 session title

当前还包含“阶段十六的第二批 Commands 扩展”：

- 新增内置命令：
  - `/context`
  - `/export`
  - `/plan`
  - `/session`
- `/plan`
  - 进入 `plan` permission mode 时尽量贴近原项目
  - 若带 prompt，会在切换后继续发起 query
- `/export`
  - 支持把当前 conversation 导出为 `.txt`
- `/context`
  - 支持查看当前 raw conversation context 快照
- `/session`
  - 当前按“remote session 尚未实现”的边界输出状态说明

当前还包含“阶段十六的第三批 Commands 扩展”：

- 新增内置命令：
  - `/diff`
  - `/hooks`
  - `/memory`
  - `/rewind`
- `/rewind`
  - 已经可以真实改写当前 session transcript
  - Textual transcript 会跟着刷新
- `/diff`
  - 支持 git working tree 差异查看
- `/memory`
  - 先按原项目常见 memory 路径约定做 inspection / init
- `/hooks`
  - 先做 hook 配置与插件 hook 声明检查
  - hook 执行体系仍未实现

当前还包含“阶段十六的交互式命令面板增强”：

- Textual 中的多条信息型命令现在不再只是往 transcript 里追加大段文本
- 会同时打开可滚动的 modal info pane
- 现在还支持 selector dialog 与 inline editor
- PromptInput 上方现在还支持独立的 prompt overlay
- transcript 现在支持 sticky prompt、new messages pill、搜索与跳转
- 当前已接入这套面板的命令包括：
  - `/status`
  - `/config`
  - `/doctor`
  - `/context`
  - `/diff`
  - `/files`
  - `/hooks`
  - `/memory`
  - `/mcp`
  - `/permissions`
  - `/plan`
  - `/plugin`
  - `/session`
  - `/tasks`
- 当前已接入 selector dialog 的命令包括：
  - `/memory`
  - `/mcp`
  - `/plugin`
  - `/rewind`
- 当前已接入 action buttons 的命令包括：
  - `/memory show <target>`
  - `/mcp show <server_name>`
  - `/plugin show <name>`
- 当前已接入 inline editor 的命令包括：
  - `/memory edit <target>`
- 当前 modal 优先级为：
  - editor
  - selector
  - info
- 当前 transcript 交互包括：
  - `Ctrl+O`
    - 在 composer 与 transcript 之间切换焦点
  - transcript 聚焦后输入 `/`
    - 打开搜索栏
  - transcript 聚焦后输入 `n` / `N`
    - 跳转下一个 / 上一个搜索结果
- REPL 兼容性保留：
  - `prompt_toolkit` REPL 仍然走文本输出
  - Textual 则额外给出更接近原项目产品感的命令面板

当前还包含“阶段十二的收尾验证与发布检查”：

- `tests/parity`
- `tests/recovery`
- `tests/stress`
- `scripts/parity_check.py`
- `scripts/stress_tool_loop.py`
- `scripts/release_check.py`

## 快速开始

```bash
cd claude_code_py
conda env create -f environment.yml
conda activate claude-code-py
claude-code-py --help
pytest
```

如果你的 `conda env create` 没有自动安装项目本身，可以补一条：

```bash
pip install -e ".[dev]"
```

如果你的环境是在第十一阶段之前创建的，记得再执行一次上面的安装命令，把 `textual` 依赖装进去。

如果你要按“原项目 REPL 完整对齐”的标准理解阶段十一，目前这一步还只能算“初版 TUI 壳层”，不是最终形态。

## 回归与发布检查

推荐在每轮较大改动后至少执行：

```bash
python scripts/parity_check.py
python scripts/stress_tool_loop.py --rounds 18
python scripts/release_check.py
```

它们分别对应：

- parity 用户契约检查
- 长工具调用回路压测
- 打包前的一键回归与发布检查

## 当前 CLI

```bash
claude-code-py --help
claude-code-py doctor
claude-code-py version
claude-code-py
claude-code-py --textual
claude-code-py -p "hello"
echo "explain this code" | claude-code-py -p
claude-code-py --textual "review this repository"
claude-code-py -p --session-id demo-1 "hello"
claude-code-py -p --session-id demo-1 "continue"
claude-code-py -p --permission-mode accept_edits --allow-tool Read "summarize this repo"
claude-code-py -p --permission-mode acceptEdits --allowed-tools Read "summarize this repo"
claude-code-py sessions
claude-code-py -p --continue "pick up where we left off"
claude-code-py -p --resume sess-1 "continue this task"
claude-code-py -p --resume sess-1 --fork-session "try a different approach"
claude-code-py -p --mcp-config .mcp.json "use the MCP tools if needed"
claude-code-py --plugin-dir /path/to/my-plugin
```

`doctor` 用于检查当前骨架的基础路径、环境和设置是否加载正常。

headless 模式的最小 transcript 当前会保存在：

- `claude_code_py/.local/state/sessions/<session_id>.jsonl`

会话索引当前会保存在：

- `claude_code_py/.local/state/session_index.sqlite3`

REPL 输入历史当前会保存在：

- `claude_code_py/.local/state/repl_history.txt`

## 当前 REPL 命令

- `/help`
  - 显示当前可用命令与可调用 skills
- `/resume`
  - 列最近会话，或恢复指定 session
- `/clear`
  - 开新会话
- `/model`
  - 查看或切换当前模型
- `/review`
  - 生成代码审查 prompt
- `/skills`
  - 列出或重载 skills
- `/status`
  - 查看当前 session / model / permission / task / MCP / plugin 状态
- `/doctor`
  - 查看环境、存储、认证配置与运行时健康信息
- `/config`
  - 查看当前运行配置快照
- `/context`
  - 查看当前 conversation context 快照
- `/export`
  - 导出当前会话到文本文件
- `/plan`
  - 切换到 plan mode，或查看当前 plan 文件
- `/diff`
  - 查看当前 git working tree 差异
- `/permissions`
  - 查看或修改当前运行时 permission mode 与 session 规则
- `/plugin`
  - 查看插件列表、错误、详情，或 reload
  - 在 `--textual` 模式下基础入口会打开 plugin selector
- `/mcp`
  - 查看 MCP server、tool 列表与单个 server 详情
  - 在 `--textual` 模式下基础入口会打开 MCP server selector
- `/files`
  - 查看当前由 `Read / Edit / Write` 进入上下文的文件
- `/hooks`
  - 查看 hook 配置文件与插件 hook 声明
- `/memory`
  - 查看常见 memory 文件路径，或初始化其中一个
  - 在 `--textual` 模式下基础入口会打开 memory file selector，并支持 inline editor
- `/rename`
  - 查看或修改当前会话标题
- `/rewind`
  - 列出 rewind 点，或把当前会话回退到更早的 user turn
  - 在 `--textual` 模式下会打开 rewind selector，并显示每个回退点的预览
- `/session`
  - 查看 remote session 状态，或说明当前为何不可用
- `/tasks`
  - 查看后台任务与详情

在 `--textual` 模式下，上面多数信息型命令会打开可滚动的 modal info pane；`/memory`、`/mcp`、`/plugin`、`/rewind` 这类 workflow 入口会打开 selector，当前优先级是 `editor > selector > info`。

## 当前 Skills 目录

- `~/.claude/skills`
- `<workspace>/.claude/skills`

基础 frontmatter 字段当前支持：

- `name`
- `description`
- `when_to_use`
- `user-invocable`
- `argument-hint`

## 当前插件目录

- `~/.claude/plugins`
- `<workspace>/.claude/plugins`
- `--plugin-dir /path/to/plugin`

最小插件结构示例：

```text
my-plugin/
├─ .claude-plugin/
│  └─ plugin.json
├─ commands/
│  └─ hello.md
└─ skills/
   └─ reviewer.md
```

最小 manifest 示例：

```json
{
  "name": "my-plugin",
  "commands": ["./commands"],
  "skills": ["./skills"]
}
```

## 当前 MCP

当前实现第一版 MCP：

- 项目级配置：`<workspace>/.mcp.json`
- CLI 配置：`--mcp-config`
- tool 命名：`mcp__<server>__<tool>`

一个最小配置示例：

```json
{
  "mcpServers": {
    "demo": {
      "command": "python",
      "args": ["server.py"]
    }
  }
}
```

HTTP MCP 也可这样配置：

```json
{
  "mcpServers": {
    "xiaohongshu-mcp": {
      "type": "http",
      "url": "http://localhost:18060/mcp"
    }
  }
}
```

## 当前权限模式

- `default`
  - headless 下默认放行；如果命中 `ask` 规则，会因为没有审批 UI 而拒绝
- `accept_edits`
  - 默认允许 `Read / Write / Edit`
- `plan`
  - 默认只允许 `Read`
- `bypass_permissions`
  - 默认放行全部工具

为了和原项目更接近，CLI 也兼容以下原始写法：

- `acceptEdits`
- `bypassPermissions`
- `--allowed-tools`
- `--disallowed-tools`
