# Claude Code Haha 交互对话上下文处理详解

本文专门分析这个项目里“**一次交互式对话**”的上下文是如何构建、更新、压缩、发送和恢复的。

这里的“交互式对话”特指：

- 从终端启动 `claude-haha`
- 进入 Ink/REPL 界面
- 用户在输入框里持续对话

不重点讨论：

- 纯 SDK/headless 一次性调用
- daemon 内部 worker 的特殊链路
- 某些公开仓库里缺实现的 feature-gated 分支

如果你只想先抓住主线，可以先记住这一句话：

**这个项目的上下文，不是一个简单的“messages 数组”而已，而是由 `消息历史 + system prompt + user/system context + 动态附件 + 工具结果 + compact/collapse/预算控制 + 持久化恢复` 共同组成的。**

---

## 1. 先给总图：一次交互对话的上下文主链路

当前交互式 REPL 的主链路大致是：

1. 用户在 [`REPL.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx) 输入内容
2. 进入 [`handlePromptSubmit.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts)
3. 进入 [`processUserInput.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts)
4. 生成新的 `user/attachment/system/progress` 消息
5. `REPL` 调用 [`query.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts)
6. `query.ts` 对当前消息做上下文裁剪、压缩、附件注入、系统上下文拼接
7. 最终通过 [`services/api/claude.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/api/claude.ts) 把上下文发给模型
8. 模型回复后，工具执行、附件追加、记忆注入、递归进入下一轮
9. 会话内容通过 [`sessionStorage.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/sessionStorage.ts) 持久化
10. `--resume` / `/resume` 时再从 transcript 里恢复上下文链

如果你按代码来理解，可以把这条链拆成 6 层：

- 输入层
- 消息层
- 附件层
- 上下文整形层
- API 发送层
- 持久化恢复层

---

## 2. 当前交互式对话到底走哪条路径

虽然项目里还有 [`QueryEngine.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/QueryEngine.ts) 这种更抽象的会话引擎，但**当前交互式 REPL 的核心路径仍然是 `REPL.tsx -> query.ts`**。

启动链路是：

1. [`bin/claude-haha`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/bin/claude-haha)
2. [`src/entrypoints/cli.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/entrypoints/cli.tsx)
3. [`src/main.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/main.tsx)
4. [`src/replLauncher.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/replLauncher.tsx)
5. [`src/screens/REPL.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx)

所以如果你问“交互对话里的上下文怎么处理”，最应该看的 4 个文件是：

- [`src/screens/REPL.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx)
- [`src/utils/handlePromptSubmit.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts)
- [`src/utils/processUserInput/processUserInput.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts)
- [`src/query.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts)

---

## 3. 这个项目里的“上下文”到底由哪些部分组成

在这个项目里，模型真正感知到的上下文可以拆成下面几类：

### 3.1 对话消息本体

也就是最直观的那部分：

- 用户消息
- assistant 消息
- 工具调用结果消息

但注意，这里的“用户消息”不一定都是真人敲的。

很多系统内部信息，最后也会被包装成 `type: 'user'` 且 `isMeta: true` 的消息，作为**模型可见、用户通常不可见**的上下文。

### 3.2 system prompt

这是模型每轮都会收到的高优先级系统提示。

来源包括：

- 默认系统提示
- agent/coordinator 模式提示
- CLI 自定义 system prompt
- appendSystemPrompt
- MCP 指令补充
- memory prompt

关键构造函数：

- [`getSystemPrompt()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/constants/prompts.ts)
- [`buildEffectiveSystemPrompt()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/systemPrompt.ts)

### 3.3 userContext / systemContext

这是除了 message history 之外，项目额外塞给模型的“每轮上下文”。

来源文件：

- [`src/context.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/context.ts)

它大致分两种：

- `getUserContext()`
  - 例如 `CLAUDE.md`
  - 当前日期
- `getSystemContext()`
  - 例如 git status 快照
  - cache breaker 注入

### 3.4 附件型上下文

这部分非常重要，也是这个项目区别于“纯 messages 数组”对话系统的关键。

来源文件：

- [`src/utils/attachments.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/attachments.ts)

附件不是简单文件上传，而是“在每轮前后动态计算出来的一批上下文片段”，例如：

- `@` 提到的文件
- IDE 当前选择的代码
- nested memory / CLAUDE.md
- relevant memories
- todo/task reminder
- plan mode / auto mode 提示
- MCP resource / MCP 指令增量
- queued command / task notification
- date change / token usage / diagnostics

### 3.5 压缩与裁剪后的上下文

为了不把整个会话历史无限制发给模型，这个项目有多层上下文控制：

- compact boundary 截断
- tool result budget
- snip
- microcompact
- auto compact
- reactive compact
- context collapse（当前公开树缺实现，但调用点和注释还在）

### 3.6 持久化恢复信息

上下文不是只在内存里活着。

项目会把对话、compact 结果、工具结果替换记录等写入 transcript 文件，后续 resume 时重新恢复。

来源文件：

- [`src/utils/sessionStorage.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/sessionStorage.ts)

---

## 4. 第一层：输入是如何被接住并转成“消息上下文”的

### 4.1 从 REPL 到 handlePromptSubmit

在 [`REPL.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx) 里，真正的提交流程由 `onSubmit` 驱动，然后调用：

- [`handlePromptSubmit()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts)

这个函数的职责不是直接调用模型，而是先做“输入预处理”。

它处理的事情包括：

- 空输入过滤
- `exit/quit/:q` 特殊处理
- `[Pasted text #N]` 引用展开
- pasted image 过滤
- immediate slash command 处理
- 当前 turn 正在运行时的队列排队逻辑
- 创建 `AbortController`
- 统一进入 `processUserInput()`

### 4.2 `history.ts` 在这里扮演什么角色

你现在打开的 [`history.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/history.ts) 很容易被误认为“对话上下文核心文件”，但它更准确地说是：

**输入历史与粘贴引用管理层，不是主上下文拼装层。**

它做的主要事情有：

- 把 pasted text 存储成 `[Pasted text #N]`
- 在真正提交前用 `expandPastedTextRefs()` 展开
- 维护当前项目的历史输入
- 把 history 存进 `history.jsonl`

所以：

- `history.ts` 影响“用户输入最终长什么样”
- 但它不直接负责 query 时的系统上下文拼装

这一点很关键。

### 4.3 `processUserInput()`：把输入变成消息

处理入口在：

- [`src/utils/processUserInput/processUserInput.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts)

这个函数先把输入拆成几类：

- 普通 prompt
- slash command
- bash command
- 图像/多 block 输入

它会做的事包括：

1. 提取字符串输入和前置内容块
2. 处理 pasted images
3. 存图片到磁盘
4. 抽取附件 `attachmentMessages`
5. 决定走：
   - `processBashCommand`
   - `processSlashCommand`
   - `processTextPrompt`

### 4.4 普通 prompt 如何变成消息

普通 prompt 最终走：

- [`processTextPrompt()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processTextPrompt.ts)

它会：

- 生成一个新的 `promptId`
- 记录 telemetry
- 把文本和图片 block 组装成 `createUserMessage(...)`
- 把附件消息附在后面

最终返回：

- `messages`
- `shouldQuery: true`

也就是说：

**从这一层开始，输入已经不再是“字符串”，而是进入统一的消息模型了。**

---

## 5. 第二层：这个项目的消息模型为什么是上下文处理核心

### 5.1 `createUserMessage()` 是关键基础设施

定义在：

- [`src/utils/messages.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts)

它的几个关键字段非常值得你记住：

- `content`
- `isMeta`
- `isVisibleInTranscriptOnly`
- `isVirtual`
- `toolUseResult`
- `permissionMode`
- `origin`

这意味着一个“用户消息”可能有完全不同的语义：

- 真实用户输入
- 工具结果承载消息
- 系统提醒
- slash command breadcrumb
- hook 附加上下文
- compact/recovery 提示

### 5.2 为什么 `isMeta` 这么重要

`isMeta: true` 基本可以理解成：

- **模型可见**
- **用户一般不直接看到**

这个项目里非常多的上下文信息都通过 `isMeta user message` 注入，例如：

- memory correction hint
- slash command 包装信息
- attachment 转换结果
- auto mode / plan mode 提醒
- relevant memories
- system reminder

所以，如果你以后读到某段逻辑在 `createUserMessage({ isMeta: true })`，脑子里要立刻反应：

**这很可能是在往模型上下文里塞“隐式提示”。**

### 5.3 不同消息类型在上下文中的角色

当前项目里，和上下文关系最密切的消息类型大致有：

- `user`
- `assistant`
- `attachment`
- `system`
- `progress`

它们进入 API 前的命运不同：

- `progress` 不会进入 API
- 一般 `system` 不会直接进入 API
- `attachment` 会被转换成 `user isMeta`
- `assistant` 会保留，但会规范化 tool_use
- `user` 会合并、裁剪、去工具引用无效块

---

## 6. 第三层：`ToolUseContext` 是对话上下文的运行时容器

在 REPL 中，每次发起 query 之前，会通过 [`REPL.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx) 里的 `getToolUseContext()` 构造一个新的上下文对象。

这个对象非常重要，因为它不是简单的“工具调用参数”，而是整个 query 期间的运行时环境。

它里面包含：

- 当前工具池 `tools`
- 当前命令列表 `commands`
- 当前 `mcpClients` / `mcpResources`
- `messages`
- `readFileState`
- `getAppState` / `setAppState`
- `setMessages`
- `setToolJSX`
- `appendSystemMessage`
- `nestedMemoryAttachmentTriggers`
- `loadedNestedMemoryPaths`
- `dynamicSkillDirTriggers`
- `discoveredSkillNames`
- `refreshTools`

这意味着：

- 附件系统读它
- 工具执行读它
- query loop 读它
- memory / MCP / skill 发现都读它

所以它几乎就是“当前 turn 的上下文总线”。

---

## 7. 第四层：query 前真正会被纳入上下文的来源

在 [`REPL.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx) 中，发起 query 之前会并行加载三类东西：

1. `getSystemPrompt(...)`
2. `getUserContext()`
3. `getSystemContext()`

然后通过：

- [`buildEffectiveSystemPrompt()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/systemPrompt.ts)
- [`appendSystemContext()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/api.ts)
- [`prependUserContext()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/api.ts)

拼成最终送往模型的上下文。

### 7.1 `getSystemPrompt()`

定义在：

- [`src/constants/prompts.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/constants/prompts.ts)

它负责构造基础系统提示，内容来源非常多，包括：

- 当前启用的工具
- output style
- env 信息
- scratchpad 指令
- memory prompt
- hooks 说明
- plan/auto/skill/MCP 相关引导

它更像“Claude Code 的世界观”。

### 7.2 `buildEffectiveSystemPrompt()`

定义在：

- [`src/utils/systemPrompt.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/systemPrompt.ts)

它负责决定最终使用哪套 system prompt，优先级大致是：

1. override system prompt
2. coordinator prompt
3. agent prompt
4. custom system prompt
5. default system prompt
6. appendSystemPrompt 追加

所以你可以把它理解成：

**system prompt 的调度器。**

### 7.3 `getUserContext()`

定义在：

- [`src/context.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/context.ts)

它最重要的内容是：

- `claudeMd`
- `currentDate`

其中：

- `claudeMd` 来自自动发现的 `CLAUDE.md` / memory files
- 当前日期每轮都会可用

并且它是 `memoize` 的，所以：

- 同一会话里不是每次都重新扫磁盘
- compact / clear 后缓存会被清掉

### 7.4 `getSystemContext()`

也在 [`context.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/context.ts)

它最重要的是：

- git status 快照
- cache breaker 注入（某些 feature 下）

这里有一个很值得注意的设计：

`gitStatus` 只是一份“对话开始时的快照”，不会在对话中自动更新。

也就是说：

- 它是会话开局的环境上下文
- 不是实时文件系统状态

---

## 8. 第五层：真正的主循环 `query.ts` 如何一步步处理上下文

当前交互式对话的上下文主处理逻辑都在：

- [`src/query.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts)

这是全项目里理解“上下文如何流动”最重要的文件之一。

### 8.1 它不是一次请求，而是一个 while 循环

`query()` / `queryLoop()` 是递归/循环型的。

每一轮都会：

1. 取当前 `state.messages`
2. 做上下文整形
3. 调模型
4. 跑工具
5. 插入工具结果和附件
6. 更新 `state.messages`
7. 再进入下一轮

所以这个项目的上下文不是：

- “发一次请求，拿一个回答”

而是：

- “消息不断演化、工具不断追加、上下文不断重算的 agentic loop”

### 8.2 当前轮的基础消息从哪里来

每轮一开始，query 会先做：

- `getMessagesAfterCompactBoundary(messages)`

定义在：

- [`src/utils/messages.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts)

这个函数的语义是：

- 如果历史里有 compact boundary，就只取“最后一次 compact 之后”的消息
- 没有 compact boundary 才取全部消息

这非常关键，因为它意味着：

**compact 不是“总结一下但历史仍全部发给模型”，而是真正把模型视角切换到 compact 后的新上下文段。**

### 8.3 tool result budget：大工具结果不会无限撑爆上下文

query 里会先调用：

- [`applyToolResultBudget()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/toolResultStorage.ts)

它做的事情是：

- 如果某个工具结果太大
- 就把完整输出持久化到磁盘
- 在消息里只保留 preview + 文件路径

也就是说：

- 大输出不会一直原样塞在后续上下文里
- 上下文里看到的是“被预算控制后的工具结果”

并且这些替换记录还会通过：

- [`recordContentReplacement()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/sessionStorage.ts)

写进 transcript，确保 resume 后仍然一致。

### 8.4 snip / microcompact / autoCompact

在真正发 API 之前，query 还会依次尝试几层压缩：

1. `snip`
2. `microcompact`
3. `contextCollapse`
4. `autoCompact`

#### snip

这是更轻量的历史裁剪。

#### microcompact

定义在：

- [`src/services/compact/microCompact.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/compact/microCompact.ts)

它主要处理：

- 旧工具结果清理
- cached microcompact
- time-based microcompact

重点不是“总结对话”，而是：

**把低价值、旧的大块工具结果从上下文里剔掉。**

#### autoCompact

定义在：

- [`src/services/compact/autoCompact.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/compact/autoCompact.ts)

它会根据：

- 当前 token 数
- 模型上下文窗口
- buffer token
- 用户是否启用 autoCompact

判断是否需要自动压缩。

如果触发，就会调用真正的 compact 逻辑。

### 8.5 真正 compact 后，上下文会变成什么

compact 的核心定义在：

- [`src/services/compact/compact.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/compact/compact.ts)

compact 完成后，不是只生成一条 summary，而是构造一组 `postCompactMessages`：

- boundaryMarker
- summaryMessages
- messagesToKeep
- attachments
- hookResults

对应函数：

- `buildPostCompactMessages(...)`

这意味着 compact 之后模型看到的上下文不是“只剩一条总结”，而是：

**`compact 边界 + 总结 + 保留消息 + 必须重注入的附件`**

### 8.6 contextCollapse：当前公开树里缺实现，但 query 已经接好了接口

query 中多处引用了：

- `services/contextCollapse/index.js`

但当前公开仓库里没有这个目录的实现文件。

从现有调用点和注释看，它的职责大致是：

- 在 autoCompact 之前先尝试更细粒度的 collapse
- 在 prompt-too-long 时先做一次 collapse drain 恢复
- 用“投影后的 collapsed view”代替更粗暴的全量 compact

所以在你阅读当前仓库时，要知道：

- query 已经为它预留了完整接入点
- 但公开树中你只能看到接口痕迹，不能完整追实现

---

## 9. 第六层：附件系统如何把“隐式上下文”塞进每一轮

这一层是整个项目最复杂、也最有代表性的上下文增强机制。

核心文件：

- [`src/utils/attachments.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/attachments.ts)

### 9.1 附件什么时候算

有两次主要时机：

#### 时机 1：用户提交输入时

在 `processUserInputBase()` 里，会先调用：

- `getAttachmentMessages(inputString, ...)`

这一步主要用来处理“和当前用户输入直接相关”的附件，例如：

- `@` 提到的文件
- MCP resource 引用
- agent mention
- skill discovery（某些 feature 下）

#### 时机 2：工具执行结束后、递归进入下一轮前

在 `query.ts` 里，工具结果收集完成后，还会再次调用：

- `getAttachmentMessages(null, updatedToolUseContext, ...)`

这一步不是围绕当前 prompt 文本，而是围绕：

- 最新 messages
- 工具执行结果
- 当前 session/plan/auto/task/memory 状态

来生成新的上下文附件。

### 9.2 附件大致分哪几类

从 `attachments.ts` 的实现看，可以把附件分成这几组：

#### A. 用户输入直接触发的附件

- `at_mentioned_files`
- `mcp_resources`
- `agent_mentions`
- `skill_discovery`

#### B. 所有线程都可能有的上下文附件

- `date_change`
- `ultrathink_effort`
- `deferred_tools_delta`
- `agent_listing_delta`
- `mcp_instructions_delta`
- `changed_files`
- `nested_memory`
- `dynamic_skill`
- `skill_listing`
- `plan_mode`
- `plan_mode_exit`
- `auto_mode`
- `auto_mode_exit`
- `todo_reminders` / `task_reminder`
- `teammate_mailbox`
- `team_context`
- `agent_pending_messages`
- `critical_system_reminder`
- `compaction_reminder`
- `context_efficiency`

#### C. 只在主线程加的附件

- `ide_selection`
- `ide_opened_file`
- `output_style`
- `diagnostics`
- `lsp_diagnostics`
- `unified_tasks`
- `async_hook_responses`
- `token_usage`
- `budget_usd`
- `output_token_usage`
- `verify_plan_reminder`

### 9.3 relevant memories 是异步预取的

这块特别值得单独说。

之前 relevant memories 可能是同步算的，但现在 query 里使用的是：

- [`startRelevantMemoryPrefetch()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/attachments.ts)

它的特点是：

- 在一轮 query 开始时就异步启动
- 主模型 streaming 和工具执行时并行跑
- 到工具结束后再尝试“消费”
- 如果这轮没来得及算完，可以下一轮再消费

所以它不是阻塞式上下文构建，而是：

**一个挂在 turn 生命周期上的异步记忆预取器。**

### 9.4 nested memory 怎么避免重复注入

`attachments.ts` 里有两个关键状态：

- `loadedNestedMemoryPaths`
- `readFileState`

它们一起用来防止：

- 同一个 CLAUDE.md / memory 文件一轮又一轮重复塞回上下文

这是因为：

- compact 之后允许重新注入
- 但在同一个 compact segment 里又要避免重复

所以它不是简单的布尔值，而是“按路径 + 生命周期阶段”的去重。

---

## 10. 第七层：为什么 attachment 最后会变成 `user isMeta`

附件本身不会直接原样发给 API。

最终会经过：

- [`normalizeAttachmentForAPI()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts)

它会把不同 attachment 类型转成一批真正的 `UserMessage`。

这些消息大多带：

- `isMeta: true`

举几个典型例子：

- `nested_memory`
  - 会转成关于 memory 文件内容的 meta user message
- `plan_mode`
  - 会转成“你现在还在 plan mode，只能读不能写”的 system-reminder
- `relevant_memories`
  - 会转成 memory 摘要文本
- `skill_listing`
  - 会转成当前可用 skills 列表
- `mcp_resource`
  - 会转成 MCP 资源内容说明

这就是为什么我前面说：

**这个项目的上下文增强，本质上大量是靠“把结构化 attachment 转成 meta user messages”实现的。**

---

## 11. 第八层：真正发 API 前，消息会怎样被标准化

核心函数：

- [`normalizeMessagesForAPI()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts)

这是上下文处理里极其关键的一步。

### 11.1 它先做的几件事

1. `reorderAttachmentsForAPI(...)`
   - 调整 attachment 的位置
2. 去掉 virtual messages
3. 建立 stripTargets
   - 如果某些 PDF/image/request-too-large 内容触发过错误，后续要从上下文里剥离

### 11.2 哪些消息不会进 API

在这一步里会显式过滤：

- `progress`
- 大部分 `system`
- synthetic API error message

所以：

**你在 REPL 里看到的消息，不等于最终发给模型的消息。**

### 11.3 user message 会被合并

因为某些后端不支持连续多个 user message，所以它会：

- 合并连续 user messages

这也是为什么 attachment 经常被合并进邻近 user 消息里。

### 11.4 assistant message 会被规范化 tool_use

assistant 消息里的 `tool_use` block 会做：

- tool 名规范化
- input 规范化
- 在不支持 tool search 时去掉 `caller` 等字段

### 11.5 attachment 会被转成 user message 再并入

也就是说 attachment 从“单独消息类型”变成“模型可见 user message”的这一跳，就发生在这里。

### 11.6 还会做一些 API 防御性修复

例如：

- 过滤 orphaned thinking-only messages
- 过滤 whitespace-only assistant messages
- 处理 tool reference sibling relocation
- 确保 tool_use / tool_result pairing 正确

这些逻辑说明：

这个项目并不信任“当前内存消息状态一定天然合法”，而是在 API 边界前再做一轮强约束整理。

---

## 12. 第九层：真正送给模型的上下文长什么样

到了 query 调模型时，最终传给 `callModel` 的核心内容大致是：

- `messages: prependUserContext(messagesForQuery, userContext)`
- `systemPrompt: appendSystemContext(systemPrompt, systemContext)`
- `tools`
- `thinkingConfig`

也就是：

### 12.1 message 侧

`prependUserContext(...)` 会在消息最前面插入一个 `isMeta user message`：

- 用 `<system-reminder>` 包住
- 里面写上：
  - `# claudeMd`
  - `# currentDate`
  - 等 userContext 项

这意味着 `userContext` 并不是 system prompt 的一部分，而是作为一条特殊 user message 放进消息头部。

### 12.2 system prompt 侧

`appendSystemContext(...)` 会把 `systemContext` 追加到 system prompt 数组尾部。

这意味着：

- `gitStatus` 之类内容属于 system prompt 侧补充
- `claudeMd` 属于 userContext 侧补充

这是该项目上下文分层里一个很关键的设计细节。

### 12.3 工具侧

工具也会影响上下文，因为：

- `getSystemPrompt(...)` 会根据工具集合生成提示
- API 层会把工具 schema 一起发给模型
- MCP 工具、ToolSearch defer_loading 也会影响模型看到的能力边界

---

## 13. 第十层：一次工具调用之后，上下文怎么继续滚动

query 不是“一次回答就结束”，而是工具结果回来后继续下一轮。

在 [`query.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts) 中，工具执行结束后会：

1. 收集 `toolResults`
2. 再次生成 attachments
3. 可选消费 relevant memory prefetch
4. 可选注入 skill discovery prefetch
5. 从队列里移除已消费的 queued commands
6. 刷新可用 tools（MCP 可能刚连上）
7. 更新 `state.messages = [...messagesForQuery, ...assistantMessages, ...toolResults]`
8. `continue` 进入下一轮

这意味着工具调用的结果不会只是“显示给用户看”，而是会成为：

- 下一轮模型上下文的一部分

所以在这个项目里，工具结果是上下文演化的核心驱动力。

---

## 14. 第十一层：中途还会插入哪些“非用户主动输入”的上下文

这是很多初学者最容易忽略的地方。

在一次长对话中，模型上下文不只受用户输入影响，还可能被这些东西主动改变：

### 14.1 queued command / task notification

query 在工具执行后，会把某些排队命令和后台任务通知转成 attachment 注入。

所以即使用户这一轮没说新话，模型也可能收到：

- 后台任务完成通知
- scheduled task 触发结果

### 14.2 stop hook / pre hook / async hook response

hook 也可能把附加上下文塞进这一轮，例如：

- hook additional context
- hook blocking error
- async hook responses

### 14.3 token usage / budget / diagnostics

这些也不是用户输入，但会被系统按 turn 注入作为 meta context。

所以：

**这个项目的上下文是“事件驱动补丁式增长”的，不是纯聊天记录。**

---

## 15. 第十二层：compact 之后缓存和上下文状态如何清理

compact 之后不是只改 `messages`，还会做很多清理动作。

关键逻辑在：

- [`runPostCompactCleanup()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/compact/postCompactCleanup.ts)

它会清掉：

- microcompact 状态
- system prompt section cache
- memory 文件缓存
- classifier approvals
- speculative checks
- session message cache

而 `/clear` 或 resume 时还会通过：

- [`clearSessionCaches()`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/clear/caches.ts)

进一步清：

- `getUserContext` / `getSystemContext` / `getGitStatus` cache
- command cache
- dynamic skills
- sent skill names
- image store
- prompt cache break detection
- session ingress caches

这说明一个事实：

**上下文在这个项目里不只是“消息”，还包含大量派生缓存；compact/clear 本质上是在重置整套上下文生态。**

---

## 16. 第十三层：上下文如何持久化，resume 时如何恢复

这部分核心文件是：

- [`src/utils/sessionStorage.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/sessionStorage.ts)

### 16.1 transcript 会写成 JSONL

交互对话的 transcript 会被写到：

- `~/.claude/projects/.../<sessionId>.jsonl`

这里面不只存普通消息，还可能存：

- summary
- custom title
- file history snapshot
- attribution snapshot
- content replacements
- contextCollapse commits/snapshot

### 16.2 为什么 content replacement 也要持久化

因为 tool result budget 可能把大工具结果替换成“落盘文件 + preview”。

如果不把这些 replacement 持久化：

- resume 后上下文会和之前不一致

所以项目专门有：

- `recordContentReplacement(...)`

来保证恢复后仍然用同一套替换视图。

### 16.3 `loadTranscriptFromFile()` 怎么恢复

恢复时会：

1. 读 transcript
2. 找叶子消息
3. 反向重建 conversation chain
4. 恢复 summary / customTitle / tag / worktree 状态
5. 恢复 contentReplacements
6. 恢复 contextCollapse 相关记录（如果有）

也就是说：

resume 不是简单“把历史消息重新显示出来”，而是重新恢复一套**可继续工作的上下文状态**。

---

## 17. 第十四层：你当前打开的几个文件，在“上下文系统”里分别是什么角色

### [`history.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/history.ts)

作用：

- 输入历史
- pasted text/image 引用
- `[Pasted text #N]` 展开

结论：

- 影响“输入会变成什么”
- 不是 query 上下文整形中心

### [`context.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/context.ts)

作用：

- `getUserContext()`
- `getSystemContext()`

结论：

- 是 system/user context 的真正来源
- 对每轮上下文非常关键

### [`cost-tracker.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/cost-tracker.ts)

作用：

- 记录 token、cost、duration、usage
- session 间恢复成本状态

结论：

- 不直接构造模型上下文
- 但会影响 `/cost`、`/stats`、budget attachment 等周边上下文提示

### [`costHook.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/costHook.ts)

作用：

- 进程退出时输出/保存 cost summary

结论：

- 属于生命周期收尾逻辑
- 不是核心上下文处理层

### [`dialogLaunchers.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/dialogLaunchers.tsx)

作用：

- 把 `main.tsx` 里的对话框懒加载逻辑拆出来

结论：

- 和“上下文注入”关系不大
- 更偏 UI 启动结构整理

---

## 18. 第十五层：最容易误解的几个点

### 18.1 “上下文 = messages” 是错的

真实情况是：

- messages 只是基础层
- 还要叠加 system prompt、user/system context、attachments、tool schemas、memory、compact 状态

### 18.2 `system` 消息不一定直接进 API

很多 `system` 消息只是 UI 反馈。

真正送给模型时，很多系统信息会被转成：

- meta user message
- attachment-normalized message

### 18.3 attachment 不是 UI 附件而已

在这个项目里，attachment 更像：

- “结构化上下文片段”

它的主要意义不是展示，而是最终转成模型可见上下文。

### 18.4 compact 不是“总结完继续把全量历史也带着”

compact 之后真正参与模型上下文的是：

- compact boundary 之后的 segment

所以 compact 是上下文重写，不只是加一个摘要。

### 18.5 `history.ts` 不是 query 核心

它很重要，但它负责的是：

- 输入历史和 pasted content 管理

不是 query 阶段的上下文主整形器。

---

## 19. 建议你按这个顺序读，最容易吃透“上下文系统”

### 第一组：先抓输入进入系统的路径

1. [`src/screens/REPL.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx)
2. [`src/utils/handlePromptSubmit.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts)
3. [`src/utils/processUserInput/processUserInput.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts)
4. [`src/utils/processUserInput/processTextPrompt.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processTextPrompt.ts)

### 第二组：再看“上下文来源”

5. [`src/context.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/context.ts)
6. [`src/constants/prompts.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/constants/prompts.ts)
7. [`src/utils/systemPrompt.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/systemPrompt.ts)

### 第三组：看“上下文增强”

8. [`src/utils/attachments.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/attachments.ts)
9. [`src/utils/messages.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts)

重点看：

- `createUserMessage`
- `normalizeMessagesForAPI`
- `getMessagesAfterCompactBoundary`
- `normalizeAttachmentForAPI`

### 第四组：看主循环如何滚动上下文

10. [`src/query.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts)

重点看：

- `messagesForQuery`
- `applyToolResultBudget`
- `microcompactMessages`
- `autoCompactIfNeeded`
- `handleStopHooks`
- 工具执行后如何递归 next turn

### 第五组：看压缩与恢复

11. [`src/services/compact/autoCompact.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/compact/autoCompact.ts)
12. [`src/services/compact/microCompact.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/compact/compact.ts)
13. [`src/services/compact/postCompactCleanup.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/compact/postCompactCleanup.ts)
14. [`src/utils/sessionStorage.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/sessionStorage.ts)

---

## 20. 最后一段总结

这个项目里，一个交互对话的上下文处理，可以浓缩成下面这句话：

**用户输入先被转成统一消息模型，然后再叠加系统提示、用户上下文、动态附件、工具结果和记忆；每轮 query 前会经过预算控制、microcompact、autoCompact 等上下文整形，最终被标准化后送往模型；对话过程又会持续写入 transcript，供后续 resume 恢复。**

如果你以后想判断某段代码到底是不是“上下文处理”的一部分，可以用这个标准：

- 它是否会影响“模型在下一轮真正看到什么”

如果会，那它就是上下文系统的一部分。

