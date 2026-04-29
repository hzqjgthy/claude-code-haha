# Claude Code Haha 工具系统总览

本文基于当前仓库中的工具注册表、工具基类、MCP 集成逻辑和工具执行链路整理，目标是帮助你从“工具系统”角度理解这个项目。

如果你之前已经看过 slash command 文档，要先区分两个概念：

- `/xxx` 是“命令系统”
- `Bash`、`Read`、`Edit`、`WebSearch`、`Agent` 这些是“工具系统”

两者关系可以简单理解为：

- slash command 更像“入口”
- tool 更像“模型真正可以调用的能力”
- 某些命令最终会把工作交给工具系统完成

---

## 1. 先给结论：这个项目的工具系统由哪几层组成

从源码看，这个项目的工具系统不是一张固定静态表，而是由四层叠起来的：

1. 静态内置工具
   - 直接在 [`src/tools.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools.ts) 中注册。
2. 条件工具
   - 也写在 `tools.ts` 中，但是否真正加入，取决于 `USER_TYPE`、feature flag、环境变量、运行模式等条件。
3. 动态 MCP 工具
   - 运行时从 MCP server 拉取，再转换成统一的 `Tool` 对象，名字通常长成 `mcp__server__tool`。
4. 特殊辅助工具
   - 例如 `ToolSearch`、`StructuredOutput`、MCP 资源读取工具等，它们更多是在系统内部承担“桥接”“延迟加载”“结构化输出”职责。

所以，理解这个系统的关键不是死记工具名，而是先吃透下面这条主链路：

`Tool.ts -> tools.ts -> assembleToolPool() -> useMergedTools()/worker tool pool -> toolExecution.ts -> 具体 Tool.call()`

---

## 2. 什么叫“工具”

工具的抽象定义在 [`src/Tool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/Tool.ts)。

这个文件里最重要的不是某个具体工具，而是 `Tool` 这个接口。它定义了一个工具至少要回答下面这些问题：

- 这个工具叫什么：`name`
- 它有没有兼容别名：`aliases`
- 模型该怎么理解这个工具：`description()`、`prompt()`
- 输入参数长什么样：`inputSchema` 或 `inputJSONSchema`
- 输出长什么样：`outputSchema`
- 工具真正执行什么逻辑：`call()`
- 它现在能不能被启用：`isEnabled()`
- 它是不是只读：`isReadOnly()`
- 它能不能并发执行：`isConcurrencySafe()`
- 它是否需要权限校验：`checkPermissions()`
- 它是否要先做输入校验：`validateInput()`
- 它是不是 MCP 工具：`isMcp`
- 它是不是延迟加载工具：`shouldDefer`
- 它是否必须首轮就暴露给模型：`alwaysLoad`

你可以把 `Tool` 看成“模型可调用能力的统一协议层”。

也就是说，不管底层是：

- 本地 shell
- 文件系统
- MCP server
- 子 agent
- 计划模式
- 远程触发器

最后都要包装成同一种 `Tool` 结构，才能进入 Claude Code 的执行主循环。

---

## 3. 工具对象最关键的几个字段

为了读源码更快，下面把 `Tool` 接口里最重要的字段翻译成人话。

| 字段 | 含义 | 学习建议 |
| --- | --- | --- |
| `name` | 模型真正看到的工具名 | 最重要 |
| `aliases` | 兼容旧名/别名 | 看迁移兼容 |
| `searchHint` | 给 `ToolSearch` 做检索提示 | 看延迟加载机制 |
| `inputSchema` | 工具输入参数定义 | 看参数结构 |
| `outputSchema` | 工具输出结构定义 | 看结果如何回传 |
| `description()` | 工具说明 | 模型决策时会看 |
| `prompt()` | 更长的使用说明 | 工具提示语来源 |
| `call()` | 真正执行逻辑 | 核心实现 |
| `isEnabled()` | 当前环境下是否启用 | 决定“会不会出现” |
| `checkPermissions()` | 权限检查 | 决定“能不能执行” |
| `validateInput()` | 输入校验 | 决定“参数是否有效” |
| `isReadOnly()` | 是否只读 | 权限与风险判定会用 |
| `isConcurrencySafe()` | 能否并发 | 流式工具执行器会用 |
| `isMcp` | 是否 MCP 工具 | 动态工具识别 |
| `shouldDefer` | 是否延迟加载 | `ToolSearch` 会用 |
| `alwaysLoad` | 是否永不延迟 | 强制首轮暴露 |
| `maxResultSizeChars` | 结果太大时如何截断/落盘 | 理解大输出处理 |

---

## 4. 工具系统的总注册表：`src/tools.ts`

项目里“所有可能的内置工具”的总入口在 [`src/tools.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools.ts)。

这个文件最重要的几个函数是：

### 4.1 `getAllBaseTools()`

这是“当前环境下，理论上可能存在的全部内置工具列表”。

注意这里的“全部”并不等于“最终一定给模型看见”，因为：

- 有的工具会再经过 `isEnabled()` 过滤
- 有的工具会被权限 deny 规则过滤
- 有的工具会在 REPL 模式下被隐藏
- 有的工具只是特殊工具，后面会再单独处理

可以把它理解成“源级别的工具候选池”。

### 4.2 `getTools(permissionContext)`

这是“真正对当前会话生效的内置工具列表”。

它会做几件事：

1. 处理 simple mode
   - 如果开启 `CLAUDE_CODE_SIMPLE`，工具集会被砍成极简版。
2. 排除特殊工具
   - 例如 `ListMcpResourcesTool`、`ReadMcpResourceTool`、`StructuredOutput`。
3. 依据 deny 规则过滤工具
   - 使用 `filterToolsByDenyRules()`。
4. 处理 REPL 模式
   - 如果启用了 `REPL`，会把 `Read`、`Edit`、`Write`、`Bash` 等原始工具从直接可见列表里隐藏。
5. 最后调用每个工具的 `isEnabled()`
   - 不满足条件的工具不会出现在最终列表中。

### 4.3 `assembleToolPool(permissionContext, mcpTools)`

这是“最终工具池的主拼装函数”。

它会把：

- 内置工具
- 运行时 MCP 工具

拼成同一套工具池，并做：

- deny 规则过滤
- 名称去重
- 排序稳定化

这个函数非常关键，因为：

- REPL 用它
- worker / subagent 也用它
- 所有真正进入 query loop 的工具集合，基本都要经过这里

### 4.4 `getMergedTools(permissionContext, mcpTools)`

这个函数和 `assembleToolPool()` 相比更宽松一些，主要用于“需要考虑所有工具（含 MCP）”的场景，例如：

- 工具搜索阈值计算
- token 统计
- 某些调试和分析逻辑

---

## 5. 工具池在界面层如何接起来

REPL 侧的关键入口是 [`src/hooks/useMergedTools.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useMergedTools.ts)。

它做的事情很简单但很重要：

1. 调用 `assembleToolPool(toolPermissionContext, mcpTools)`
2. 再把初始化阶段传入的 `initialTools` 合并进去
3. 返回“当前 REPL 真正使用的工具池”

这意味着：

- 工具不是写死在某个组件里
- 工具池是随着权限上下文、MCP 状态、模式切换动态变化的

所以你在 REPL 里看到的工具集合，本质上是“状态计算结果”，不是一个常量。

---

## 6. 动态 MCP 工具是怎么来的

这一块是整个工具系统里最值得重点学习的部分之一。

核心文件是：

- [`src/services/mcp/client.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/mcp/client.ts)
- [`src/tools/MCPTool/MCPTool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/MCPTool/MCPTool.ts)

### 6.1 基本思路

MCP 工具不是在 `tools.ts` 里一条条静态写死的。

实际流程是：

1. Claude Code 先连上某个 MCP server
2. 调用 MCP 的 `tools/list`
3. 拿到 server 返回的工具定义
4. 在 [`fetchToolsForClient()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/mcp/client.ts) 中，把它们转换成项目自己的 `Tool` 对象
5. 放进 `appState.mcp.tools`
6. 最后由 `assembleToolPool()` 和内置工具合并

### 6.2 动态 MCP 工具的命名

默认情况下，MCP 工具名会被转换成：

`mcp__<serverName>__<toolName>`

例如：

- `mcp__slack__send_message`
- `mcp__playwright__screenshot`
- `mcp__claude-in-chrome__tabs_context_mcp`

这样做的好处是：

- 能区分不同 server 的同名工具
- 权限规则可以精确到 server 级或具体 tool 级
- 在日志与 telemetry 中更容易归类

### 6.3 MCP 工具也会被包装成统一 `Tool`

在 `fetchToolsForClient()` 里，MCP server 返回的工具会被改造成统一格式，补上：

- `name`
- `mcpInfo`
- `isMcp: true`
- `searchHint`
- `alwaysLoad`
- `description()`
- `inputJSONSchema`
- `checkPermissions()`

也就是说，从系统角度看，MCP 工具和本地 `Bash` / `Read` / `Edit` 没有本质区别，都是统一的 `Tool`。

### 6.4 MCP 资源工具是“按需注入”的

项目里有两个和 MCP 资源相关的辅助工具：

- `ListMcpResourcesTool`
- `ReadMcpResourceTool`

注意这两个工具虽然也出现在 `getAllBaseTools()` 里，但 `getTools()` 会把它们从普通内置工具列表中排掉。

它们真正加入工具池的方式是：

- 只有当某个 MCP server 声明自己支持 `resources`
- 才在 MCP 连接逻辑中按需注入这两个工具

这意味着它们属于“跟 MCP 能力一起出现的辅助工具”，不是普通固定工具。

---

## 7. ToolSearch：为什么有些工具不会一开始就完整暴露

这一块的核心文件是：

- [`src/utils/toolSearch.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/toolSearch.ts)
- [`src/tools/ToolSearchTool/ToolSearchTool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/ToolSearchTool/ToolSearchTool.ts)

### 7.1 背景

如果把所有 MCP 工具、扩展工具、实验工具一次性全放进 prompt：

- token 会爆炸
- 系统提示词缓存会变差
- 模型首轮看到的工具太多，选择也更混乱

所以这个项目引入了“延迟工具加载”机制。

### 7.2 哪些工具会被延迟

原则上：

- 所有 MCP 工具默认都是 deferred
- 某些内置工具如果 `shouldDefer === true`，也会被延迟

但也有例外：

- `ToolSearch` 自己不能延迟
- `Agent` 在某些 fork-subagent 场景下不能延迟
- `SendUserMessage` 这种一上来就要用到的工具也不能延迟
- 设置了 `alwaysLoad: true` 的工具不会延迟

### 7.3 ToolSearch 做什么

当一个 deferred tool 还没有完整 schema 时，模型不能直接调用它。

这时模型需要先调用：

- `ToolSearch`

把目标工具的完整 schema 拉进上下文，然后才能真正使用该工具。

所以 `ToolSearch` 本质上是“工具系统里的工具加载器”。

---

## 8. 工具执行链路：从 tool_use 到结果回写

这一部分的核心文件是 [`src/services/tools/toolExecution.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts)。

你可以把它理解成“工具调用调度中心”。

最重要的函数是：

- `runToolUse()`

### 8.1 `runToolUse()` 做了什么

整体流程大致是：

1. 根据工具名在当前工具池里找工具
   - 先查 `toolUseContext.options.tools`
   - 再兼容旧 alias 的 fallback
2. 如果找不到工具，直接返回错误
3. 如果找到了，就开始执行真正的调用流程
4. 进入 `streamedCheckPermissionsAndCallTool()`
5. 过程中持续产出 progress message
6. 最终生成 `tool_result`

### 8.2 真正执行前要过哪些关

一个工具真正跑起来之前，通常会经历这些步骤：

1. 输入检查
   - `validateInput()`
2. 权限检查
   - `checkPermissions()`
3. hook 处理
   - `PreToolUse` / `PostToolUse`
4. 正式执行
   - `tool.call()`
5. 结果映射
   - `mapToolResultToToolResultBlockParam()`
6. UI 渲染
   - `renderToolUseMessage()`
   - `renderToolResultMessage()`

这说明工具系统不是“模型一调用就直接跑代码”，而是中间还套了：

- 权限系统
- hook 系统
- telemetry
- 输出预算控制
- UI 渲染层

---

## 9. REPL 模式和 Simple 模式对工具集的影响

这是阅读 `tools.ts` 时最容易漏掉的一层。

### 9.1 Simple 模式

如果开启 `CLAUDE_CODE_SIMPLE`：

- 普通情况下只保留：
  - `Bash`
  - `Read`
  - `Edit`
- 如果同时启用了 coordinator mode，还会补上：
  - `Agent`
  - `TaskStop`
  - `SendMessage`

也就是说，simple mode 会大幅收缩工具面。

### 9.2 REPL 模式

REPL 模式的逻辑在 [`src/tools/REPLTool/constants.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/REPLTool/constants.ts)。

一旦启用了 `REPL` 工具，下面这些原始工具会从“直接给模型看的列表”里隐藏：

- `Read`
- `Write`
- `Edit`
- `Glob`
- `Grep`
- `Bash`
- `NotebookEdit`
- `Agent`

原因是：

- 它们会被包装进 REPL VM 里统一使用
- 不希望模型同时看到“原始工具”和“REPL 包装工具”，导致混乱

---

## 10. 当前项目里最重要的内置工具清单

下面按学习视角，把当前仓库里的核心工具分组整理。

注意：

- 这里统计的是“源码里明确注册过、且在当前仓库能看见主要实现入口”的工具
- 条件工具会在下一节单独说明
- 这里说的“工具名”优先用模型真正看到的 `name`

### 10.1 文件与代码操作工具

| 工具名 | 来源目录 | 作用 |
| --- | --- | --- |
| `Bash` | `src/tools/BashTool` | 执行 shell 命令 |
| `Read` | `src/tools/FileReadTool` | 读取文件、图片、PDF、notebook |
| `Edit` | `src/tools/FileEditTool` | 原地修改已有文件 |
| `Write` | `src/tools/FileWriteTool` | 创建或覆盖文件 |
| `NotebookEdit` | `src/tools/NotebookEditTool` | 专门编辑 Jupyter notebook |
| `Glob` | `src/tools/GlobTool` | 按名称模式查找文件 |
| `Grep` | `src/tools/GrepTool` | 按内容正则搜索 |
| `PowerShell` | `src/tools/PowerShellTool` | Windows/PowerShell 场景下的命令执行 |

这一组工具是代码代理最核心的一层能力。

如果你只想理解“Claude Code 为什么能改代码”，优先读这一组。

### 10.2 Web 与信息获取工具

| 工具名 | 来源目录 | 作用 |
| --- | --- | --- |
| `WebSearch` | `src/tools/WebSearchTool` | 联网搜索最新信息 |
| `WebFetch` | `src/tools/WebFetchTool` | 读取指定 URL 并抽取内容 |

其中：

- `WebSearch` 更偏“搜索结果汇总”
- `WebFetch` 更偏“精读某个具体页面”

### 10.3 用户交互与输出工具

| 工具名 | 来源目录 | 作用 |
| --- | --- | --- |
| `AskUserQuestion` | `src/tools/AskUserQuestionTool` | 向用户发结构化选择题 |
| `SendUserMessage` | `src/tools/BriefTool` | 给用户输出真正可见的消息 |
| `Skill` | `src/tools/SkillTool` | 调用 slash-command skill |

这一组里最值得注意的是：

- `BriefTool` 的真实工具名不是 `Brief`
- 它对模型暴露的名字是 `SendUserMessage`
- 旧名 `Brief` 只是兼容 alias

### 10.4 代理、计划与协作工具

| 工具名 | 来源目录 | 作用 |
| --- | --- | --- |
| `Agent` | `src/tools/AgentTool` | 派生子 agent 执行任务 |
| `EnterPlanMode` | `src/tools/EnterPlanModeTool` | 切换到 plan mode |
| `ExitPlanMode` | `src/tools/ExitPlanModeTool` | 提交计划并退出 plan mode |
| `SendMessage` | `src/tools/SendMessageTool` | 给 swarm/teammate 发消息 |
| `TeamCreate` | `src/tools/TeamCreateTool` | 创建多 agent 团队 |
| `TeamDelete` | `src/tools/TeamDeleteTool` | 解散多 agent 团队 |

这一组体现的是：这个项目不只是“单 agent + 单工具调用”，它还支持：

- 计划模式
- 多 agent 协作
- team/swarm 模式

### 10.5 任务与后台执行工具

| 工具名 | 来源目录 | 作用 |
| --- | --- | --- |
| `TodoWrite` | `src/tools/TodoWriteTool` | 管理当前会话的待办清单 |
| `TaskCreate` | `src/tools/TaskCreateTool` | 创建结构化任务 |
| `TaskGet` | `src/tools/TaskGetTool` | 根据 ID 查看任务 |
| `TaskUpdate` | `src/tools/TaskUpdateTool` | 更新任务 |
| `TaskList` | `src/tools/TaskListTool` | 列出全部任务 |
| `TaskOutput` | `src/tools/TaskOutputTool` | 查看后台任务输出 |
| `TaskStop` | `src/tools/TaskStopTool` | 停止后台任务 |

这一组工具说明项目内部实际上有两层任务系统：

- 一层是更轻量的 `TodoWrite`
- 一层是更结构化的 `TaskCreate/Get/Update/List`

### 10.6 工作区与环境切换工具

| 工具名 | 来源目录 | 作用 |
| --- | --- | --- |
| `EnterWorktree` | `src/tools/EnterWorktreeTool` | 创建并切入隔离 worktree |
| `ExitWorktree` | `src/tools/ExitWorktreeTool` | 退出 worktree |
| `Config` | `src/tools/ConfigTool` | 读写 Claude Code 设置 |
| `tungsten` | `src/tools/TungstenTool` | 内部/ant 环境工具 |

其中：

- `Config` 只在 `USER_TYPE === 'ant'` 时加入基础工具列表
- `EnterWorktree` / `ExitWorktree` 在当前代码里已经是全量开启能力

### 10.7 MCP 辅助工具

| 工具名 | 来源目录 | 作用 |
| --- | --- | --- |
| `ListMcpResourcesTool` | `src/tools/ListMcpResourcesTool` | 列出 MCP 资源 |
| `ReadMcpResourceTool` | `src/tools/ReadMcpResourceTool` | 读取 MCP 资源 |
| `mcp__server__tool` | 动态生成 | 真正的 MCP server 工具 |

这里要特别注意：

- `src/tools/MCPTool` 是“动态 MCP 工具的统一包装模板”
- 它不是一个普通固定工具名
- 模型真正看到的 MCP 工具名一般是 `mcp__xxx__yyy`

### 10.8 工具加载与结构化辅助工具

| 工具名 | 来源目录 | 作用 |
| --- | --- | --- |
| `ToolSearch` | `src/tools/ToolSearchTool` | 加载 deferred tool 的完整 schema |
| `StructuredOutput` | `src/tools/SyntheticOutputTool` | 内部结构化输出工具 |

其中：

- `ToolSearch` 是对模型显式开放的工具
- `StructuredOutput` 更偏内部系统辅助工具，常用于 `--json-schema` 一类结构化输出场景

---

## 11. 一些“目录名”和“工具名”不一致的典型例子

读这个项目时，最容易搞混的一点是：目录名不等于工具名。

下面列几个最重要的映射：

| 目录/实现 | 实际工具名 | 备注 |
| --- | --- | --- |
| `BriefTool` | `SendUserMessage` | `Brief` 只是旧 alias |
| `AgentTool` | `Agent` | 旧 alias 是 `Task` |
| `FileReadTool` | `Read` | 不是 `FileRead` |
| `FileEditTool` | `Edit` | 不是 `FileEdit` |
| `FileWriteTool` | `Write` | 不是 `FileWrite` |
| `NotebookEditTool` | `NotebookEdit` | 与目录名一致 |
| `ListMcpResourcesTool` | `ListMcpResourcesTool` | 但 UI 常显示 `listMcpResources` |
| `ReadMcpResourceTool` | `ReadMcpResourceTool` | 但 UI 常显示 `readMcpResource` |

所以你读工具代码时，最好同时关注三件事：

- 目录名
- `name`
- `userFacingName()`

---

## 12. 条件工具：哪些能力不是默认总会出现

下面这些工具在 `tools.ts` 中是条件加入的。

### 12.1 当前仓库中有主要实现入口的条件工具

| 工具 | 条件 | 备注 |
| --- | --- | --- |
| `PowerShell` | `isPowerShellToolEnabled()` | Windows 场景 |
| `LSP` | `ENABLE_LSP_TOOL` | 语言服务器能力 |
| `TaskCreate/Get/Update/List` | `isTodoV2Enabled()` | 交互模式默认开，非交互可由 env 强制开 |
| `TeamCreate/TeamDelete` | `isAgentSwarmsEnabled()` | 多 agent 团队 |
| `CronCreate/Delete/List` | `feature('AGENT_TRIGGERS')` | 定时调度 |
| `RemoteTrigger` | `feature('AGENT_TRIGGERS_REMOTE')` | 远程触发器 API |
| `ToolSearch` | `isToolSearchEnabledOptimistic()` | 工具延迟加载 |
| `Config` | `USER_TYPE === 'ant'` | 内部/ant 环境 |
| `tungsten` | `USER_TYPE === 'ant'` | 内部工具 |

### 12.2 当前源码树中只有部分文件或缺实现的条件工具

从当前仓库树来看，下面这些工具在 `tools.ts` 中被引用，但当前公开源码里没有完整实现文件，或者只有部分残留文件：

| 工具/模块 | 当前状态 | 说明 |
| --- | --- | --- |
| `REPLTool` | 只有 `constants.ts`、`primitiveTools.ts` | 主实现缺失 |
| `SuggestBackgroundPRTool` | 缺实现文件 | ant-only 条件工具 |
| `SleepTool` | 只有 `prompt.ts` | 主实现缺失 |
| `WorkflowTool` | 只有 `constants.ts` | 主实现缺失 |
| `MonitorTool` | 缺实现文件 | feature-gated |
| `SendUserFileTool` | 缺实现文件 | feature-gated |
| `PushNotificationTool` | 缺实现文件 | feature-gated |
| `SubscribePRTool` | 缺实现文件 | feature-gated |
| `VerifyPlanExecutionTool` | 缺实现文件 | env-gated |
| `OverflowTestTool` | 缺实现文件 | feature-gated |
| `CtxInspectTool` | 缺实现文件 | feature-gated |
| `TerminalCaptureTool` | 缺实现文件 | feature-gated |
| `WebBrowserTool` | 缺实现文件 | feature-gated |
| `SnipTool` | 缺实现文件 | feature-gated |
| `ListPeersTool` | 缺实现文件 | feature-gated |

这意味着：

- 这个项目的“设计出来的工具系统”比当前公开源码树更大
- 你在 `tools.ts` 里看到的能力边界，未必都能在本地源码里完整追到实现

---

## 13. 这个项目里“命令”和“工具”的关系

学习到这里，最好再把 slash command 和 tool 重新串一下。

最简单的理解方式是：

### 13.1 命令负责“进入某条流程”

例如：

- `/permissions`
- `/review`
- `/init`

它们控制的是：

- UI 入口
- prompt 模板
- 配置面板
- 特定工作流

### 13.2 工具负责“模型能做什么”

例如：

- `Bash`
- `Read`
- `Edit`
- `Agent`
- `WebSearch`

它们控制的是：

- 执行 shell
- 读写文件
- 发子 agent
- 联网搜索

### 13.3 命令和工具会互相调用

常见情况包括：

- 某个 slash command 展开成 prompt
- prompt 再驱动模型去使用工具
- 某些本地命令本身不经模型
- 但它们会修改工具上下文、权限模式、MCP 状态、计划模式等

所以如果你想从整体上理解项目：

- 命令系统是“入口层”
- 工具系统是“能力层”

---

## 14. 阅读工具系统，建议按这个顺序看源码

### 第一步：先看工具抽象

1. [`src/Tool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/Tool.ts)

先搞清楚什么是一个 `Tool`，尤其看：

- `Tool` 接口
- `toolMatchesName()`
- `findToolByName()`

### 第二步：再看工具注册表

2. [`src/tools.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools.ts)

重点看：

- `getAllBaseTools()`
- `getTools()`
- `assembleToolPool()`
- `getMergedTools()`

### 第三步：看 REPL 如何拿到工具池

3. [`src/hooks/useMergedTools.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useMergedTools.ts)

这一步帮助你理解：

- UI 层看到的工具集合是怎么来的

### 第四步：看 MCP 动态工具生成

4. [`src/services/mcp/client.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/mcp/client.ts)

重点看：

- `fetchToolsForClient()`
- MCP 工具如何变成统一的 `Tool`
- MCP 资源工具如何按需注入

### 第五步：看工具延迟加载

5. [`src/utils/toolSearch.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/toolSearch.ts)
6. [`src/tools/ToolSearchTool/ToolSearchTool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/ToolSearchTool/ToolSearchTool.ts)

重点看：

- 什么是 deferred tool
- 为什么 `ToolSearch` 存在

### 第六步：看工具执行链路

7. [`src/services/tools/toolExecution.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts)

重点看：

- `runToolUse()`
- 查找工具
- 权限检查
- hook 处理
- tool_result 返回

### 第七步：最后挑几个典型工具精读

推荐顺序：

1. [`src/tools/BashTool/BashTool.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/BashTool/BashTool.tsx)
2. [`src/tools/FileReadTool/FileReadTool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileReadTool/FileReadTool.ts)
3. [`src/tools/FileEditTool/FileEditTool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileEditTool/FileEditTool.ts)
4. [`src/tools/AgentTool/AgentTool.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/AgentTool/AgentTool.tsx)
5. [`src/tools/SkillTool/SkillTool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/SkillTool/SkillTool.ts)
6. [`src/tools/WebSearchTool/WebSearchTool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/WebSearchTool/WebSearchTool.ts)

---

## 15. 一句话总结

这个项目的工具系统，本质上是一个“统一能力协议层”：

- 本地文件操作被包装成工具
- shell 执行被包装成工具
- 计划模式被包装成工具
- 子 agent 被包装成工具
- MCP 服务器返回的远程能力也被包装成工具

最后，它们都通过 `Tool.ts` 里的统一接口，进入同一条：

`注册 -> 过滤 -> 拼装 -> 执行 -> 权限 -> hook -> 结果回写`

如果你把这份文档配合下面几个文件一起读：

- [`src/Tool.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/Tool.ts)
- [`src/tools.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools.ts)
- [`src/services/mcp/client.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/mcp/client.ts)
- [`src/services/tools/toolExecution.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts)

基本就能把这个项目的工具系统主干吃透。
