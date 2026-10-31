# Python 重构版与原项目详细对比

## 1. 文档目的

这份文档用于回答一个非常具体的问题：

**当前 `claude_code_py/` 和原始 TypeScript/Bun 项目相比，到底已经实现了什么，还缺什么。**

本文不是阶段总结，而是面向后续继续重构时使用的**差距清单**。  
阅读这份文档后，你应该能清楚知道：

- Python 版已经覆盖了原项目哪些主线能力
- 哪些能力只是“有雏形”，还不能算真正对齐
- 哪些能力目前基本没有开始
- 后面如果继续按原项目补齐，优先级应该怎样排

---

## 2. 对比基准

本次对比基于当前仓库中的两个代码区：

- 原项目：
  - `src/`
  - 入口为 `bin/claude-haha`
  - 默认走 `src/entrypoints/cli.tsx`
- Python 重构版：
  - `claude_code_py/src/claude_code_py/`
  - 入口为 `claude_code_py/src/claude_code_py/cli/main.py`

本文结论基于**当前仓库快照**，不是基于早期规划文档的理想状态。

---

## 3. 一页结论

如果一句话总结当前状态：

**Python 版已经把“最核心的基础骨架”做出来了，但和原项目相比，仍然主要停留在“核心主线可运行、产品外围能力大量缺失”的阶段。**

更具体地说：

- 已经落地的主线：
  - CLI 基础入口
  - `--print` 无头模式
  - 基础 Query Loop
  - 基础工具系统
  - 基础权限系统
  - 会话持久化 / resume / fork
  - REPL
  - Skills / Plugins / MCP 基础支持
  - 进程内 Agent / 后台任务
  - 初版 Textual TUI
  - 基础 parity / recovery / stress / release 检查

- 已经开始但还远未对齐原项目的主线：
  - Textual TUI
  - 交互式权限审批
  - 多 Agent / 任务体系
  - MCP
  - remote provider 抽象

- 目前差距最大的区域：
  - 原项目完整 Ink REPL 体验
  - 大量 slash commands
  - 大量工具
  - remote / bridge / direct connect / SSH
  - 复杂权限系统与 sandbox 交互
  - compact / memory / telemetry / auth / IDE / LSP / voice / desktop / mobile 等产品级外围能力

结论上，当前 Python 版更接近：

**“Claude Code 核心运行骨架的独立 Python 版”**

而不是：

**“原项目完整产品能力的 1:1 Python 平移版”**

---

## 4. 规模对比

下面这组数据能帮助你快速理解差距量级。

### 4.1 总体规模

| 项目 | 源码文件数 | 代码行数 |
|---|---:|---:|
| 原项目 `src/` | 1916 | 513642 |
| Python 版 `claude_code_py/src/claude_code_py/` | 101 | 6555 |

这意味着：

- Python 版当前源码体量大约只有原项目 `src` 的很小一部分
- 因此“还有差距”不是个别模块没写，而是整体产品覆盖度仍然明显不足

### 4.2 几个关键子系统的规模差距

| 功能域 | 原项目 | Python 版 |
|---|---:|---:|
| Commands | `src/commands` 207 文件 | `claude_code_py/.../commands` 12 文件 |
| Tools | `src/tools` 187 文件 | `claude_code_py/.../tools` 10 文件 |
| UI | `src/components` 389 文件 | `claude_code_py/.../ui` 14 文件 |
| Services | `src/services` 130 文件 | Python 版没有对应规模的服务层 |
| Bridge / Remote | `src/bridge` 31 文件 + `src/remote` 4 文件 | `providers/remote` 3 文件 |
| Hooks | `src/hooks` 104 文件 | Python 版无同等级 hooks 层 |

这组数据很重要，因为它说明：

- Python 版目前的重点仍然是“核心链路打通”
- 原项目大量复杂度来自产品级 UI、命令、工具、桥接、远程、服务化能力
- 这些区域在 Python 版当前大多只是基础替身或尚未实现

---

## 5. 功能对比矩阵

下面是按功能域整理的总体状态。

状态说明：

- `已实现`：已有可运行实现，且主线能力基本成立
- `部分实现`：有骨架或基础版，但和原项目还有明显差距
- `未实现`：当前基本没有对应能力

| 功能域 | 原项目状态 | Python 版状态 | 结论 |
|---|---|---|---|
| CLI 基础入口 | 完整 | 已实现 | 基础 CLI 可用 |
| 多入口 fast-path | 很完整 | 未实现 | 差距很大 |
| `--print` 无头模式 | 很完整 | 部分实现 | 只覆盖最小主线 |
| 交互式 REPL | 完整 Ink REPL | 部分实现 | 有 REPL，但体验差距大 |
| 完整 TUI | 完整产品级 TUI | 部分实现 | 只有初版 Textual UI |
| Query Loop | 完整 | 已实现 | 核心链路已建立 |
| 工具系统 | 很完整 | 部分实现 | 只有小部分核心工具 |
| 权限系统 | 很完整 | 部分实现 | 基础规则有了，高级能力差距大 |
| 会话持久化 / 恢复 | 完整 | 已实现 | 主线能力基本到位 |
| compact / memory | 完整 | 未实现 | 当前为空白 |
| slash commands | 很完整 | 部分实现 | 只有少量基础命令 |
| skills | 完整 | 已实现 | 基础链路可用 |
| MCP | 很完整 | 部分实现 | 仅基础 stdio/http + tool 注册 |
| 插件系统 | 很完整 | 部分实现 | 仅本地插件加载 |
| 多 Agent / 任务 | 很完整 | 部分实现 | 仅进程内子代理与简化任务 |
| remote / bridge | 很完整 | 未实现 | 只有 provider 抽象 |
| auth / account / policy | 完整 | 未实现 | 当前无同级实现 |
| IDE / LSP / computer-use | 完整 | 未实现 | 当前基本为空 |
| telemetry / analytics | 完整 | 未实现 | 当前为空 |
| 发布前回归体系 | 原项目成熟 | 部分实现 | 已有基础检查脚本，但不等价 |

---

## 6. Python 版已经实现的部分

为了避免只盯着缺失项，先明确当前 Python 版已经做成了哪些“可用主线”。

### 6.1 入口与运行主线

已经实现：

- `claude-code-py --help`
- `claude-code-py doctor`
- `claude-code-py version`
- `claude-code-py -p`
- `claude-code-py` 进入 `prompt_toolkit` REPL
- `claude-code-py --textual` 进入 Textual TUI

对应模块：

- `app/*`
- `cli/main.py`
- `cli/print_mode.py`
- `cli/repl_mode.py`
- `cli/textual_mode.py`

### 6.2 核心 Query / Tool Loop

已经实现：

- `QueryRequest / QueryResult`
- provider 完成一次 completion
- tool call -> tool result -> 回填消息
- 多轮工具循环

对应模块：

- `application/query_service.py`
- `application/tool_service.py`
- `providers/llm/base.py`

### 6.3 核心工具

已经实现：

- `Bash`
- `Read`
- `Edit`
- `Write`
- `WebFetch`
- `Agent`
- `MCP` tool wrapper

对应模块：

- `tools/bash.py`
- `tools/file_read.py`
- `tools/file_edit.py`
- `tools/file_write.py`
- `tools/web_fetch.py`
- `tools/agent.py`
- `tools/mcp.py`

### 6.4 权限与交互审批基础

已经实现：

- `allow / deny / ask`
- 规则来源：
  - session
  - user settings
  - project settings
  - cli args
- TUI 中的交互式 ask 审批
- session 级记忆 allow/deny

对应模块：

- `domain/permissions.py`
- `permissions/engine.py`
- `permissions/rules.py`
- `application/permission_service.py`
- `ui/textual/dialogs.py`

### 6.5 会话与恢复

已经实现：

- JSONL transcript
- SQLite session index
- `--resume`
- `--continue`
- `--fork-session`
- transcript 缺索引时回填 summary

对应模块：

- `application/session_service.py`
- `providers/storage/transcript_store.py`
- `providers/storage/session_index.py`
- `session/recovery.py`

### 6.6 命令、skills、plugins、MCP、tasks

已经实现：

- 内置 slash commands：
  - `/help`
  - `/resume`
  - `/clear`
  - `/model`
  - `/review`
  - `/skills`
  - `/tasks`
- markdown skills
- 本地插件加载
- MCP config loader + stdio/http client
- 进程内子代理与后台任务

---

## 7. 还没有实现的功能：按领域详细拆解

下面是最重要的部分。

### 7.1 CLI 入口与运行模式差距

原项目的入口远不只是一个普通 CLI。

原项目已有但 Python 版当前未实现的入口能力包括：

- `remote-control` / `rc` / `remote` / `sync` / `bridge`
- `daemon`
- `--daemon-worker`
- `environment-runner`
- `self-hosted-runner`
- `--worktree --tmux` fast-path
- `--computer-use-mcp`
- Chrome native host / Claude in Chrome MCP 相关入口
- 背景 session 管理：
  - `ps`
  - `logs`
  - `attach`
  - `kill`
  - `--bg` / `--background`

对应原项目文件：

- `src/entrypoints/cli.tsx`
- `src/bridge/*`
- `src/daemon/*`
- `src/environment-runner/*`
- `src/self-hosted-runner/*`
- `src/cli/bg.ts`

Python 版当前情况：

- 只有基础 CLI
- 没有多入口分发层
- 没有这些长生命周期运行模式

结论：

- **入口层只实现了最核心的一小部分**

### 7.2 `--print` / Headless 能力差距

原项目的 `src/cli/print.ts` 是一个超大模块，功能远超“给我一个 prompt 然后打印结果”。

原项目已有但 Python 版当前缺失或明显不足的能力包括：

- 结构化 I/O
- 复杂 transport：
  - SSE
  - WebSocket
  - HybridTransport
- `structuredIO`
- `remoteIO`
- permission prompt tool
- 远程桥接下的 control message 处理
- 大量 headless mode 下的 session / task / stop / cron / reconnect 编排
- 更复杂的流式输出和事件上传

对应原项目文件：

- `src/cli/print.ts`
- `src/cli/structuredIO.ts`
- `src/cli/remoteIO.ts`
- `src/cli/transports/*`

Python 版当前情况：

- 只支持基础 `-p/--print`
- 输出格式仅 `text/json`
- 无 structured IO 协议
- 无 remote headless transport

结论：

- **Python 版 headless 只是 MVP，不是原项目同等级 headless runtime**

### 7.3 交互式 UI / REPL 差距

原项目的交互核心在：

- `src/screens/REPL.tsx`
- `src/components/*`
- `src/hooks/*`
- `src/ink/*`

这是一个很重的产品级 TUI，不是只有 transcript 和 input。

当前 Python 版已经有：

- `prompt_toolkit` REPL
- Textual 初版 TUI
- 状态栏
- transcript
- 任务面板
- 权限弹窗

但和原项目相比，仍缺少大量交互层能力：

- `FullscreenLayout` 那种滚动区 / 底部区 / overlay / modal 分层
- PromptInput 的完整输入体验：
  - suggestion
  - history search
  - mode indicator
  - queued commands
  - footer suggestions
  - placeholder 逻辑
  - 更多键绑定
- transcript 内消息动作：
  - cursor navigation
  - rewind
  - message actions
  - search / selector
- 各类启动 / 中途 / 完成时的通知与提示
- spinner / thinking / tool progress 的完整视觉层
- remote callout
- IDE status indicator
- surveys / onboarding / trust / install prompts
- fullscreen transcript 辅助能力

对应原项目组件示例：

- `src/components/PromptInput/*`
- `src/components/StatusLine.tsx`
- `src/components/Messages.tsx`
- `src/components/FullscreenLayout.tsx`
- `src/components/MessageSelector.tsx`
- `src/components/TaskListV2.tsx`
- `src/components/RemoteCallout.tsx`
- `src/components/FeedbackSurvey/*`
- `src/components/IdeOnboardingDialog.tsx`

结论：

- **Python 版 UI 现在是“有结构的初版”，不是原项目同等级产品 UI**

### 7.4 slash commands 差距

原项目命令体系极其庞大。

原项目 `src/commands` 当前有 207 个文件，覆盖大量功能。

Python 版当前只有少量基础命令：

- `/help`
- `/resume`
- `/clear`
- `/model`
- `/review`
- `/skills`
- `/tasks`

原项目中大量未实现的命令包括：

- `add-dir`
- `agents`
- `branch`
- `bridge`
- `btw`
- `chrome`
- `compact`
- `config`
- `context`
- `copy`
- `cost`
- `diff`
- `doctor`
- `effort`
- `export`
- `fast`
- `feedback`
- `files`
- `hooks`
- `ide`
- `install-*`
- `login`
- `logout`
- `memory`
- `mobile`
- `output-style`
- `permissions`
- `plan`
- `plugin`
- `rate-limit-options`
- `remote-env`
- `remote-setup`
- `rename`
- `rewind`
- `sandbox-toggle`
- `session`
- `share`
- `status`
- `tag`
- `teleport`
- `theme`
- `vim`
- `voice`

结论：

- **命令系统当前只覆盖了最基础的一小部分**

### 7.5 工具系统差距

原项目工具层远比当前 Python 版大。

原项目 `src/tools` 当前有 187 个文件，涉及大量专用工具。

Python 版当前工具只有：

- `Bash`
- `Read`
- `Edit`
- `Write`
- `WebFetch`
- `Agent`
- `MCP`

原项目中典型但尚未实现的工具包括：

- `AskUserQuestionTool`
- `BriefTool`
- `ConfigTool`
- `EnterPlanModeTool`
- `ExitPlanModeTool`
- `EnterWorktreeTool`
- `ExitWorktreeTool`
- `GlobTool`
- `GrepTool`
- `LSPTool`
- `ListMcpResourcesTool`
- `ReadMcpResourceTool`
- `McpAuthTool`
- `NotebookEditTool`
- `PowerShellTool`
- `REPLTool`
- `RemoteTriggerTool`
- `ScheduleCronTool`
- `SendMessageTool`
- `SkillTool`
- `SleepTool`
- `SyntheticOutputTool`
- `TaskCreate/Get/List/Output/Stop/Update`
- `TeamCreate/Delete`
- `TodoWriteTool`
- `ToolSearchTool`
- `TungstenTool`
- `WebSearchTool`
- `WorkflowTool`

结论：

- **工具系统只实现了核心文件/命令/网页抓取主线，离原项目完整工具面差距很大**

### 7.6 权限系统差距

Python 版现在已经有一套基础权限系统，这一点很重要。  
但原项目的权限体系复杂度明显更高。

原项目已有但 Python 版当前仍缺失或明显不足的部分包括：

- 按工具类型区分的专用审批 UI：
  - Bash
  - WebFetch
  - FileWrite
  - FileEdit
  - NotebookEdit
  - PowerShell
  - Sandbox network
  - AskUserQuestion
  - Skill permission
  - Enter/Exit plan mode
- 更复杂的 “always allow / deny / persist / suggestion” 交互
- shell / powershell 规则匹配与危险模式分析
- auto mode / bypass permissions 的完整切换逻辑
- sandbox adapter 深度联动
- rule shadowing 检测
- denial tracking
- classifier / heuristic / hook 并行联动
- worker / leader 权限同步

对应原项目文件示例：

- `src/components/permissions/*`
- `src/utils/permissions/*`
- `src/utils/sandbox/sandbox-adapter.ts`
- `src/utils/swarm/permissionSync.ts`

结论：

- **Python 版权限系统有主线，但还不是原项目那种产品级安全交互系统**

### 7.7 Session / Memory / Compact 差距

Python 版当前做到了：

- transcript
- index
- resume / continue / fork

但原项目还包含很多“长期使用”能力，当前 Python 版几乎没覆盖：

- conversation compact
- micro compact
- post compact cleanup
- session memory
- extract memories
- file history snapshot / rewind
- rename session
- export transcript
- share transcript
- worktree state 持久化
- session backgrounding / concurrent session management
- remote transcript hydration

对应原项目文件示例：

- `src/services/compact/*`
- `src/services/SessionMemory/*`
- `src/utils/sessionStorage.ts`
- `src/utils/fileHistory.ts`
- `src/utils/sessionRestore.ts`

结论：

- **Python 版恢复能力只覆盖了基础 transcript 级别，长期会话管理能力差距明显**

### 7.8 MCP 能力差距

Python 版当前 MCP 已经实现：

- `.mcp.json`
- stdio / HTTP
- 动态注册 MCP tools

这已经覆盖了最基础的 MCP 主线。  
但原项目的 MCP 远不止这些。

原项目已有但 Python 版当前缺失的能力包括：

- MCP auth / OAuth
- MCP 资源读取与资源列表
- MCP reconnect / connectivity 状态
- elicitation dialog
- official registry
- xaa / vscode SDK MCP / claude.ai 相关集成
- channel permissions / notification
- 更复杂的配置归一化和 env expansion
- 更完整的连接生命周期管理

对应原项目文件示例：

- `src/services/mcp/*`
- `src/components/mcp/*`
- `src/commands/mcp/*`

结论：

- **Python 版 MCP 目前是基础客户端级别，不是原项目完整 MCP 平台**

### 7.9 插件系统差距

Python 版当前插件系统已实现：

- 本地目录扫描
- manifest 读取
- 本地 commands / skills 加载

但原项目插件系统还包含：

- marketplace
- browse / discover / manage
- trust warning
- install / validate / update
- autoupdate notification
- marketplace 配置管理
- 远程来源插件处理

对应原项目文件示例：

- `src/commands/plugin/*`
- `src/services/plugins/*`
- `src/utils/plugins/*`

结论：

- **当前 Python 版插件系统只是“本地插件加载器”，不是原项目完整插件生态**

### 7.10 Agent / Tasks / Team / Swarm 差距

Python 版当前已实现：

- `Agent` 工具
- 进程内子代理
- 后台任务
- `/tasks`

但原项目在这方面已经扩展到更复杂的协作结构：

- `LocalAgentTask`
- `RemoteAgentTask`
- `InProcessTeammateTask`
- `DreamTask`
- Shell task 族
- teammate / team / swarm
- leader / worker 权限桥接
- task detail dialogs
- task output tools
- teammate lifecycle notification

对应原项目文件示例：

- `src/tasks/*`
- `src/components/tasks/*`
- `src/utils/swarm/*`
- `src/tools/AgentTool/*`

结论：

- **Python 版目前只有“单机简化版子代理任务系统”**

### 7.11 Remote / Bridge / Direct Connect / SSH 差距

这是当前差距最大的区域之一。

原项目已有：

- Remote session manager
- Remote session websocket
- bridge main
- repl bridge
- bridge transport
- remote permission bridge
- direct connect
- SSH session
- reconnect / archive / heartbeat / ingress / session url

对应原项目文件示例：

- `src/bridge/*`
- `src/remote/*`
- `src/cli/remoteIO.ts`
- `src/hooks/useRemoteSession.ts`
- `src/hooks/useDirectConnect.ts`
- `src/hooks/useSSHSession.ts`

Python 版当前情况：

- 只有 `RemoteProvider` 抽象
- 只有 `LocalRemoteProvider`
- TUI 里只能展示 remote status

结论：

- **remote 目前几乎还没开始真正实现**

### 7.12 Auth / Account / Policy / Analytics 差距

原项目已有大量账号、策略、遥测相关能力：

- OAuth
- login / logout
- account 状态
- policy limits
- remote managed settings
- analytics / datadog / growthbook
- feature gating
- billing / extra usage / passes / rate limit options
- updater / release notes / deprecation notifications

对应原项目文件示例：

- `src/services/oauth/*`
- `src/services/analytics/*`
- `src/services/policyLimits/*`
- `src/services/remoteManagedSettings/*`
- `src/cli/update.ts`
- `src/commands/login/*`
- `src/commands/logout/*`
- `src/commands/passes/*`

Python 版当前情况：

- 基本没有这一级别的体系

结论：

- **这些产品级账户/运营/策略能力几乎全部缺失**

### 7.13 IDE / LSP / Voice / Desktop / Mobile / Computer Use 差距

原项目中还有不少“产品外围但真实存在”的能力：

- IDE integration
- LSP
- desktop onboarding / desktop upsell
- mobile commands
- voice mode
- Chrome / Claude in Chrome
- computer-use / screenshot / accessibility 相关

对应原项目文件示例：

- `src/commands/ide/*`
- `src/services/lsp/*`
- `src/commands/mobile/*`
- `src/commands/voice/*`
- `src/utils/computerUse/*`
- `src/utils/claudeInChrome/*`

Python 版当前情况：

- 当前基本没有对应实现

结论：

- **这一整圈产品外围能力基本还没进入 Python 版**

---

## 8. 哪些地方最容易被误判为“已经完成”

下面这些点尤其容易产生误判。

### 8.1 “有 Textual UI” 不等于 “完成 REPL 对齐”

当前 Python 版确实已经有：

- Textual 状态栏
- transcript
- prompt composer
- task panel
- 权限弹窗

但和原项目 `src/screens/REPL.tsx` 相比，这还只是初版骨架。  
原项目交互层还有大量：

- layout 组织
- overlay 编排
- footer suggestions
- message actions
- history search
- remote callout
- IDE 状态
- 各类通知 / 引导 / survey

所以：

- **TUI 已经开始，不等于 TUI 已经对齐**

### 8.2 “有 MCP” 不等于 “MCP 平台完成”

当前 Python 版 MCP 只等于：

- 可以连接一些 MCP server
- 可以把 tool 暴露出来

还不等于：

- auth
- resources
- reconnect
- registry
- elicitation
- 完整 UI

### 8.3 “有 Agent 工具” 不等于 “原项目多 Agent 完成”

当前 Python 版的 Agent 更接近：

- 简化进程内子代理

还不等于：

- remote agents
- teammates
- leader/worker
- team/swarm
- 复杂任务视图

### 8.4 “有 parity 测试” 不等于 “已经和原项目做了真正 1:1 对拍”

当前第十二阶段新增的 parity 测试，本质上是：

- **契约级回归测试**

它们验证的是：

- Python 版内部是否满足当前定义的用户契约

它们**不是**：

- 直接同时调用原项目二进制和 Python 版二进制，然后逐项比对输出

所以这类 parity 更准确地说是：

- “面向原项目关键行为的对齐回归”

而不是：

- “严格的双实现逐条对拍框架”

---

## 9. 当前最重要的缺失功能清单

如果只列“最值得继续补”的部分，我建议重点看这张表。

| 优先级 | 功能域 | 说明 |
|---|---|---|
| P0 | 完整 REPL 交互层 | 这是原项目的核心产品形态 |
| P0 | commands 扩展 | 当前命令面太薄 |
| P0 | tools 扩展 | 当前工具面太薄 |
| P0 | 权限系统高级能力 | 关系到安全边界与真实可用性 |
| P0 | remote / bridge | 原项目的重要产品特征，当前几乎缺失 |
| P1 | compact / memory / file history | 长会话可用性关键 |
| P1 | MCP 资源、auth、registry、elicitation | MCP 目前仍是基础版 |
| P1 | 插件 marketplace / trust / install | 当前只有本地加载 |
| P1 | 多 Agent / teammate / swarm | 当前只是简化版 |
| P2 | IDE / LSP / voice / desktop / mobile | 产品外围能力 |
| P2 | telemetry / auth / billing / updater | 产品运营能力 |

---

## 10. 建议的后续补齐顺序

如果后续你还要继续严格参考原项目补齐，我建议顺序如下：

### 第一步：先把 REPL 交互层做深

优先对齐：

- `src/screens/REPL.tsx`
- `src/components/FullscreenLayout.tsx`
- `src/components/PromptInput/*`
- `src/components/Messages.tsx`
- `src/components/StatusLine.tsx`
- `src/components/tasks/*`
- `src/components/permissions/*`

原因：

- 这是原项目最中心的用户体验层
- 很多能力不是“缺一个命令”，而是缺整个交互容器

### 第二步：再补工具与命令面

优先补：

- `Glob`
- `Grep`
- `TodoWrite`
- `WebSearch`
- `PowerShell`
- `NotebookEdit`
- `Task*`
- `Team*`

再补命令：

- `config`
- `diff`
- `permissions`
- `status`
- `theme`
- `memory`
- `compact`
- `plugin`
- `mcp`

### 第三步：补 remote / bridge / direct connect

这是最能拉近和原项目“产品级差距”的区域。

优先看：

- `src/bridge/*`
- `src/remote/*`
- `src/cli/remoteIO.ts`

### 第四步：补长期会话能力

优先看：

- compact
- session memory
- file history
- export/share

### 第五步：最后补产品外围能力

包括：

- auth
- policy
- analytics
- IDE / LSP
- voice
- desktop / mobile

---

## 11. 最终结论

当前 Python 版已经不是“空骨架”了。

它已经完成了：

- 独立项目结构
- 核心 query/tool/session/permission 主线
- skills / plugins / MCP 基础链路
- 简化的 agent / tasks
- 初版 TUI
- 一套基本可重复执行的测试与发布检查

但是，如果标准是：

**“严格参考原项目功能，做到完整 Python 重构”**

那么当前状态仍然只能算：

**完成了核心骨架与主线路径，离原项目完整产品能力仍有明显距离。**

最本质的差距不在于“少几个文件”，而在于：

- 原项目是一个大型产品平台
- Python 版目前还是一个已经具备核心能力的独立重构骨架

因此，后续最关键的工作不只是“继续加功能”，而是：

- 按原项目的模块边界继续补齐
- 尤其是 REPL 交互层、工具层、命令层、权限层、remote 层

