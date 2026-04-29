# Claude Code Haha 一次实际交互执行链路追踪

本文专门追踪你截图里的这次真实交互：

1. 在终端里执行 `./bin/claude-haha`
2. 进入 REPL/TUI 界面
3. 输入 `帮我在当前目录下写一个helloworld.py脚本`
4. 界面显示 `⎿ Selected 1 lines from docs_thy/安装步骤.md in Cursor`
5. 模型发出 `Write(helloworld.py)`
6. 工具执行后显示 `Wrote 1 lines to helloworld.py`
7. 最终模型再回复 `已创建 helloworld.py。`

这条链路里最重要的结论先说清楚：

- 这不是“一次模型回复直接完成”的流程，而是至少两轮模型交互。
- 第一轮模型的任务是“决定是否调用工具，以及调用哪个工具”，所以它发出了 `Write`。
- 工具真正把文件写到磁盘后，客户端把工具结果塞回消息历史里。
- 第二轮模型再根据工具结果，生成自然语言答复 `已创建 helloworld.py。`

你可以把它理解成：

`用户输入 -> 客户端组织上下文 -> 模型决定调用 Write -> 客户端执行 Write 落盘 -> 客户端把 tool_result 回喂模型 -> 模型输出最终中文回复`

---

## 1. 启动阶段：`./bin/claude-haha` 如何进入 REPL

你执行的 `./bin/claude-haha` 只是一个 Bash 包装入口，不是真正的业务逻辑入口。它做了两件核心事情：

- 把当前目录切到项目根目录，保证后续相对路径稳定
- 最终 `exec bun ... ./src/entrypoints/cli.tsx`

对应源码：

- [bin/claude-haha](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/bin/claude-haha)
- [bin/claude-haha:22](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/bin/claude-haha#L22)
- [bin/claude-haha:30](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/bin/claude-haha#L30)
- [bin/claude-haha:67](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/bin/claude-haha#L67)

接下来 `src/entrypoints/cli.tsx` 在模块加载后直接执行 `main()`，再动态导入真正的 CLI 主程序 `src/main.tsx`：

- [src/entrypoints/cli.tsx:34](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/entrypoints/cli.tsx#L34)
- [src/entrypoints/cli.tsx:296](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/entrypoints/cli.tsx#L296)
- [src/entrypoints/cli.tsx:306](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/entrypoints/cli.tsx#L306)

`src/main.tsx` 是真正的大入口。默认交互模式下，它最终会调用 `launchRepl(...)`，把 App 和 REPL 渲染出来：

- [src/main.tsx:585](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/main.tsx#L585)
- [src/main.tsx:3804](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/main.tsx#L3804)
- [src/replLauncher.tsx:12](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/replLauncher.tsx#L12)

`launchRepl` 做的事情很直白：加载 `App` 和 `REPL` 组件，然后开始跑终端界面：

- [src/replLauncher.tsx:15](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/replLauncher.tsx#L15)
- [src/replLauncher.tsx:19](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/replLauncher.tsx#L19)

所以启动链路可以缩成一句话：

`bin/claude-haha -> entrypoints/cli.tsx -> main.tsx -> launchRepl -> REPL`

---

## 2. 你按下 Enter 之后，是谁先接住了这次提交

这部分是很多人第一次看源码时最容易绕晕的。

### 2.1 REPL 把 `onSubmit` 传给 `PromptInput`

在 REPL 渲染阶段，`PromptInput` 组件拿到了一个 `onSubmit={onSubmit}`：

- [src/screens/REPL.tsx:4903](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L4903)
- [src/screens/REPL.tsx:4905](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L4905)

而这个 `onSubmit` 本身是在 REPL 内部定义的：

- [src/screens/REPL.tsx:3142](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L3142)

### 2.2 `PromptInput` 再把 `onSubmit` 传给底层 `TextInput`

`PromptInput` 并不是自己直接监听 Enter 做提交，它把 `onSubmit` 作为 `baseProps` 的一部分传给底层输入组件：

- [src/components/PromptInput/PromptInput.tsx:2172](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/PromptInput/PromptInput.tsx#L2172)
- [src/components/PromptInput/PromptInput.tsx:2174](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/PromptInput/PromptInput.tsx#L2174)
- [src/components/PromptInput/PromptInput.tsx:2243](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/PromptInput/PromptInput.tsx#L2243)

同时它还有一个 `chat:submit` 的 keybinding 注册，但源码注释明确说了：普通 Enter 提交主要由 `TextInput` 直接处理，这个注册更多是给 chord/keybinding 场景使用的：

- [src/components/PromptInput/PromptInput.tsx:1637](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/PromptInput/PromptInput.tsx#L1637)
- [src/components/PromptInput/PromptInput.tsx:1650](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/PromptInput/PromptInput.tsx#L1650)

### 2.3 真正接住 Enter 的是 `useTextInput`

`TextInput` 内部调用 `useTextInput(...)`，把 `props.onSubmit` 继续往下传：

- [src/components/TextInput.tsx:92](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/TextInput.tsx#L92)
- [src/components/TextInput.tsx:95](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/TextInput.tsx#L95)

在 `useTextInput.ts` 里，`key.return` 会进入 `handleEnter(key)`：

- [src/hooks/useTextInput.ts:366](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useTextInput.ts#L366)
- [src/hooks/useTextInput.ts:368](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useTextInput.ts#L368)

`handleEnter` 的规则是：

- 如果前一个字符是 `\`，插入换行
- 如果是 `Meta+Enter` 或 `Shift+Enter`，插入换行
- 否则调用 `onSubmit?.(originalValue)`

源码：

- [src/hooks/useTextInput.ts:247](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useTextInput.ts#L247)
- [src/hooks/useTextInput.ts:258](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useTextInput.ts#L258)
- [src/hooks/useTextInput.ts:266](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useTextInput.ts#L266)

所以这一步最准确的表述是：

`Enter` 先被底层输入系统 `useTextInput` 捕获，然后调用了从 REPL 透传下来的 `onSubmit`。

---

## 3. `REPL.onSubmit` 收到文本后做了什么

REPL 里的 `onSubmit` 很长，因为它要兼容很多模式：普通 prompt、slash command、remote mode、speculation、队列等。

你的这次输入是普通中文文本：

`帮我在当前目录下写一个helloworld.py脚本`

所以它走的是“普通 prompt 提交”路径。

关键动作在这里：

- 清理输入框状态
- 记录提交计数
- 等待 session start hooks
- 调用 `handlePromptSubmit(...)`

源码位置：

- [src/screens/REPL.tsx:3339](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L3339)
- [src/screens/REPL.tsx:3358](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L3358)
- [src/screens/REPL.tsx:3488](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L3488)
- [src/screens/REPL.tsx:3490](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L3490)

也就是说，真正的“用户输入处理入口”不是直接进模型，而是先进：

`REPL.onSubmit -> handlePromptSubmit`

---

## 4. `handlePromptSubmit` 如何把这次输入转成“可查询”的消息

`handlePromptSubmit` 的职责是“把一段原始输入，整理成系统真正能处理的一次 turn”。

对应源码：

- [src/utils/handlePromptSubmit.ts:120](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts#L120)

它先处理一些外围逻辑：

- 空输入直接返回
- `exit/quit` 这类命令改写成 `/exit`
- 展开粘贴引用
- 管理排队/并发保护

例如：

- [src/utils/handlePromptSubmit.ts:174](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts#L174)
- [src/utils/handlePromptSubmit.ts:188](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts#L188)
- [src/utils/handlePromptSubmit.ts:216](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts#L216)

然后它在 `executeUserInput` 阶段，统一调用 `processUserInput(...)`：

- [src/utils/handlePromptSubmit.ts:476](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts#L476)

处理完之后，如果生成了 `newMessages`，它会调用 `onQuery(...)`，把这些消息交给后续模型查询链路：

- [src/utils/handlePromptSubmit.ts:541](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts#L541)
- [src/utils/handlePromptSubmit.ts:560](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts#L560)

这里非常关键：

`handlePromptSubmit` 自己不负责“调用模型”，它负责“把原始输入加工成消息，然后交给 onQuery”。

---

## 5. 为什么会出现 `Selected 1 lines from docs_thy/安装步骤.md in Cursor`

你截图里这行：

`⎿ Selected 1 lines from docs_thy/安装步骤.md in Cursor`

不是模型回复，也不是工具输出，而是一个 attachment message。

### 5.1 IDE 选区是怎么被收集到的

项目里有一个 `useIdeSelection` hook，专门监听 IDE/MCP 发来的 `selection_changed` 通知，然后把当前选中的文件、起始行、文本内容存起来：

- [src/hooks/useIdeSelection.ts:59](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useIdeSelection.ts#L59)
- [src/hooks/useIdeSelection.ts:91](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useIdeSelection.ts#L91)
- [src/hooks/useIdeSelection.ts:100](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useIdeSelection.ts#L100)
- [src/hooks/useIdeSelection.ts:112](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useIdeSelection.ts#L112)

### 5.2 输入处理时，IDE 选区会被做成 attachment

在附件收集逻辑里，主线程会尝试把当前 IDE 选区转成 attachment：

- [src/utils/attachments.ts:943](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/attachments.ts#L943)
- [src/utils/attachments.ts:946](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/attachments.ts#L946)

真正生成 attachment 的函数是 `getSelectedLinesFromIDE(...)`。它会产出：

- `type: 'selected_lines_in_ide'`
- `lineStart / lineEnd`
- `filename`
- `content`
- `displayPath`
- `ideName`

源码：

- [src/utils/attachments.ts:1614](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/attachments.ts#L1614)
- [src/utils/attachments.ts:1635](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/attachments.ts#L1635)

### 5.3 这行提示为什么会被显示成你看到的样子

attachment 的 UI 渲染在 `AttachmentMessage.tsx` 里，`selected_lines_in_ide` 的显示模板就是：

`⧉ Selected N lines from <displayPath> in <ideName>`

源码：

- [src/components/messages/AttachmentMessage.tsx:158](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/messages/AttachmentMessage.tsx#L158)
- [src/components/messages/AttachmentMessage.tsx:160](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/messages/AttachmentMessage.tsx#L160)

### 5.4 这段选区会不会进入模型上下文

会，而且是 model-visible 的。

在 `utils/messages.ts` 里，`selected_lines_in_ide` 会被转成一条隐藏的 meta user message，大意是：

`The user selected the lines ... from ... This may or may not be related to the current task.`

源码：

- [src/utils/messages.ts:3613](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts#L3613)
- [src/utils/messages.ts:3622](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts#L3622)

所以你看到的那一行，本质上是：

- UI 上显示成一条附件提示
- 同时又被转换成模型可见的隐式上下文

结合你截图，当时 Cursor 里正选中了 [docs_thy/安装步骤.md](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/docs_thy/安装步骤.md)，而且你选中的内容就是 `./bin/claude-haha` 那一行，所以这条上下文很自然被带进了这次 turn。

这里我做一个谨慎判断：

- 从功能上说，这条 IDE 选区“可能相关，也可能不相关”
- 对“帮我写一个 helloworld.py”这个任务来说，模型完全可能只靠你的自然语言指令就决定调用 `Write`
- 所以它更像是“被自动注入的附加上下文”，不一定是这次建文件成功的关键原因

这部分是基于源码和你截图做出的推断，不是代码里写死的因果关系。

---

## 6. 这次输入为什么会走“普通文本 prompt”路径，而不是斜杠命令/命令模式

`processUserInput(...)` 是统一入口：

- [src/utils/processUserInput/processUserInput.ts:85](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts#L85)

它最终会走到 `processUserInputBase(...)`，并在这里先收集 attachment：

- [src/utils/processUserInput/processUserInput.ts:153](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts#L153)
- [src/utils/processUserInput/processUserInput.ts:501](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts#L501)
- [src/utils/processUserInput/processUserInput.ts:504](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts#L504)

然后它会按顺序判断：

- 是否是 bash 模式
- 是否是 slash command
- 否则就是 regular user prompt

你的输入既不是 `/permissions` 这种 slash command，也不是 bash 模式，所以最后落到：

- [src/utils/processUserInput/processUserInput.ts:517](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts#L517)
- [src/utils/processUserInput/processUserInput.ts:531](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts#L531)
- [src/utils/processUserInput/processUserInput.ts:576](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts#L576)

也就是 `processTextPrompt(...)`：

- [src/utils/processUserInput/processTextPrompt.ts:19](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processTextPrompt.ts#L19)

`processTextPrompt` 会创建一个 `userMessage`，并把 attachment messages 一起返回：

- [src/utils/processUserInput/processTextPrompt.ts:89](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processTextPrompt.ts#L89)
- [src/utils/processUserInput/processTextPrompt.ts:96](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processTextPrompt.ts#L96)

这一点很重要：

客户端此时还没有决定“要不要写文件”。  
它只是把你的自然语言输入，连同 IDE 选区等附件，一起整理成一组消息。

---

## 7. `onQueryImpl` 如何组织真正发给模型的上下文

当 `handlePromptSubmit` 调用 `onQuery(...)` 之后，REPL 最终会进入 `onQueryImpl(...)`：

- [src/screens/REPL.tsx:2918](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2918)
- [src/screens/REPL.tsx:2661](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2661)

### 7.1 先构造 `toolUseContext`

`getToolUseContext(...)` 会把本轮要用到的很多运行时信息装起来：

- 可用 tools
- mcpClients
- 当前 messages
- appState 读取函数
- 通知能力
- 文件历史状态

源码：

- [src/screens/REPL.tsx:2392](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2392)
- [src/screens/REPL.tsx:2404](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2404)
- [src/screens/REPL.tsx:2413](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2413)

这意味着：模型能调用哪些工具，不是固定写死在 prompt 里的，而是这一刻由 `toolUseContext.options.tools` 动态算出来的。

### 7.2 再加载系统提示词、用户上下文、系统上下文

`onQueryImpl` 里会并行拉这些内容：

- 默认 system prompt
- userContext
- systemContext

源码：

- [src/screens/REPL.tsx:2767](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2767)
- [src/screens/REPL.tsx:2772](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2772)

其中默认 system prompt 来自：

- [src/constants/prompts.ts:444](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/constants/prompts.ts#L444)

有效 system prompt 的最终拼装来自：

- [src/utils/systemPrompt.ts:41](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/systemPrompt.ts#L41)
- [src/screens/REPL.tsx:2781](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2781)

`userContext` / `systemContext` 分别来自：

- [src/context.ts:116](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/context.ts#L116)
- [src/context.ts:155](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/context.ts#L155)

### 7.3 最后进入 `query(...)`

这里才真正开始“模型查询循环”：

- [src/screens/REPL.tsx:2793](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2793)
- [src/query.ts:219](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L219)

---

## 8. 第一次模型请求是怎么组织的

`query.ts` 是整个“模型 <-> 工具 <-> 模型”循环的核心。

### 8.1 在 query 层，用户上下文会被 prepend，系统上下文会被 append

`query.ts` 调用模型时使用：

- `prependUserContext(messagesForQuery, userContext)`
- `appendSystemContext(systemPrompt, systemContext)`

源码：

- [src/query.ts:660](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L660)
- [src/query.ts:450](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L450)
- [src/utils/api.ts:437](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/api.ts#L437)
- [src/utils/api.ts:449](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/api.ts#L449)

也就是说，真正发给模型的不是只有“你输入的那一句中文”。

还包括：

- 这轮之前的消息历史
- IDE 选区这种 attachment 转出来的 meta message
- userContext
- system prompt
- systemContext
- 当前可用工具 schema

### 8.2 到了 provider 层，还会做一次 API 规范化

在 API 适配层，消息会经过 `normalizeMessagesForAPI(...)`，system prompt 会被拆成 block：

- [src/services/api/claude.ts:1266](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/api/claude.ts#L1266)
- [src/services/api/claude.ts:3213](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/api/claude.ts#L3213)

这一步的意义是：把内部消息结构转成底层模型 API 真正需要的格式。

---

## 9. 为什么界面会先出现 `Write(helloworld.py)`

这是第一轮模型在“流式输出 tool_use”。

### 9.1 模型先输出的是 `tool_use` block，不是最终自然语言

在 provider 流里，`content_block_start` 遇到 `tool_use` 时，会先建立一个工具调用 block，输入一开始还是空字符串：

- [src/services/api/claude.ts:1995](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/api/claude.ts#L1995)
- [src/services/api/claude.ts:1997](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/api/claude.ts#L1997)
- [src/services/api/claude.ts:2000](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/api/claude.ts#L2000)

后续 `input_json_delta` 会把工具参数一点点补全：

- [src/services/api/claude.ts:2087](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/api/claude.ts#L2087)

### 9.2 REPL 收到 `tool_use` 后，把它显示为 streaming tool use

`handleMessageFromStream(...)` 在看到 `content_block_start` 且 block 类型为 `tool_use` 时，会把这次工具调用放进 `streamingToolUses`：

- [src/utils/messages.ts:2930](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts#L2930)
- [src/utils/messages.ts:3002](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts#L3002)
- [src/utils/messages.ts:3019](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts#L3019)
- [src/utils/messages.ts:3023](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts#L3023)
- [src/utils/messages.ts:3056](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts#L3056)

`REPL.onQueryEvent` 会把这些更新写进 React state：

- [src/screens/REPL.tsx:2584](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx#L2584)

### 9.3 `streamingToolUses` 会被渲染成一条“伪 assistant message”

`Messages.tsx` 会把 `streamingToolUses` 转成 synthetic streaming tool use messages：

- [src/components/Messages.tsx:443](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/Messages.tsx#L443)
- [src/components/Messages.tsx:447](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/Messages.tsx#L447)
- [src/components/Messages.tsx:448](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/Messages.tsx#L448)

### 9.4 为什么显示成 `Write(helloworld.py)` 而不是别的

在工具 UI 渲染里：

- 工具名来自 `userFacingName(...)`，对于 FileWriteTool 返回 `Write`
- 括号里的参数来自 `renderToolUseMessage(...)`，它显示 `file_path`

源码：

- [src/tools/FileWriteTool/prompt.ts:3](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/prompt.ts#L3)
- [src/tools/FileWriteTool/FileWriteTool.ts:95](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L95)
- [src/tools/FileWriteTool/UI.tsx:128](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx#L128)
- [src/tools/FileWriteTool/UI.tsx:135](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx#L135)
- [src/tools/FileWriteTool/UI.tsx:165](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx#L165)
- [src/tools/FileWriteTool/UI.tsx:180](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx#L180)
- [src/components/messages/AssistantToolUseMessage.tsx:163](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/messages/AssistantToolUseMessage.tsx#L163)
- [src/components/messages/AssistantToolUseMessage.tsx:178](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/messages/AssistantToolUseMessage.tsx#L178)

所以 `Write(helloworld.py)` 的含义是：

- `Write`：模型选中的工具名
- `helloworld.py`：模型在 tool input 里填的 `file_path`

要特别注意：

`helloworld.py` 这个路径不是客户端帮模型脑补出来的，而是模型自己在 tool input JSON 里给出的。

同理，`print("Hello, World!")` 这样的文件内容也不是客户端写死的，而是模型作为 `Write` 工具参数生成的。

---

## 10. `Write` 工具是怎么真的把文件写到磁盘上的

这部分是“显示工具调用”和“真的执行工具”的分界线。

### 10.1 query 层在发现有 `tool_use` 后，会进入工具执行阶段

在 `query.ts` 里，只要 assistant message 里出现了 `tool_use` block，就会把 `needsFollowUp = true`：

- [src/query.ts:829](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L829)
- [src/query.ts:834](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L834)

后面会执行工具更新流：

- 可能是 `StreamingToolExecutor`
- 也可能是普通的 `runTools(...)`

源码：

- [src/query.ts:1366](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L1366)
- [src/query.ts:1380](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L1380)

无论哪条分支，最终都会落到真正的单工具执行入口 `runToolUse(...)`：

- [src/services/tools/toolExecution.ts:337](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts#L337)

### 10.2 `runToolUse` 会找到名为 `Write` 的工具定义

`runToolUse` 会根据 `toolUse.name` 去可用工具池里查工具：

- [src/services/tools/toolExecution.ts:343](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts#L343)
- [src/services/tools/toolExecution.ts:345](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts#L345)

因为 FileWriteTool 的名字就是 `Write`：

- [src/tools/FileWriteTool/prompt.ts:3](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/prompt.ts#L3)
- [src/tools/FileWriteTool/FileWriteTool.ts:94](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L94)

### 10.3 真正执行前，要先做 schema 校验、输入校验、权限检查

`checkPermissionsAndCallTool(...)` 负责这一层：

- [src/services/tools/toolExecution.ts:599](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts#L599)
- [src/services/tools/toolExecution.ts:615](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts#L615)
- [src/services/tools/toolExecution.ts:683](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts#L683)

### 10.4 为什么新文件可以直接写，不需要先读

`FileWriteTool.validateInput(...)` 的逻辑是：

- 如果目标文件不存在，`stat` 抛 `ENOENT`
- 这种情况下直接返回 `{ result: true }`

源码：

- [src/tools/FileWriteTool/FileWriteTool.ts:153](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L153)
- [src/tools/FileWriteTool/FileWriteTool.ts:188](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L188)
- [src/tools/FileWriteTool/FileWriteTool.ts:192](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L192)

这正好符合你的场景：`helloworld.py` 是新建文件。

如果它是已存在文件，源码会要求先读再写，否则可能报：

`File has not been read yet. Read it first before writing to it.`

### 10.5 真正写文件的地方是 `FileWriteTool.call(...)`

核心执行在这里：

- 展开相对路径到完整路径
- 确保父目录存在
- 读取旧文件元信息
- 调用 `writeTextContent(...)` 写入内容
- 更新 LSP/VSCode/文件历史状态
- 返回 `type: 'create'`

源码：

- [src/tools/FileWriteTool/FileWriteTool.ts:223](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L223)
- [src/tools/FileWriteTool/FileWriteTool.ts:229](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L229)
- [src/tools/FileWriteTool/FileWriteTool.ts:254](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L254)
- [src/tools/FileWriteTool/FileWriteTool.ts:305](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L305)
- [src/tools/FileWriteTool/FileWriteTool.ts:395](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L395)

由于你是从项目根目录运行 `./bin/claude-haha`，模型又传了相对路径 `helloworld.py`，所以它最终写到的就是当前工作目录下的：

`/home/ad/tianhaoyang/Claude_Code/claude-code-haha/helloworld.py`

---

## 11. 为什么界面里显示的是 `Wrote 1 lines to helloworld.py`

这行很容易和“模型看到的 tool_result”混淆。

其实这里有两套结果：

### 11.1 模型可见的 tool_result

`FileWriteTool.mapToolResultToToolResultBlockParam(...)` 会把新建文件的结果映射成：

`File created successfully at: helloworld.py`

源码：

- [src/tools/FileWriteTool/FileWriteTool.ts:418](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L418)
- [src/tools/FileWriteTool/FileWriteTool.ts:424](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts#L424)

这是回喂给模型的结果文本。

### 11.2 用户界面看到的工具结果卡片

而 UI 层渲染新建文件结果时，显示的是：

`Wrote <numLines> lines to <file>`

源码：

- [src/tools/FileWriteTool/UI.tsx:39](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx#L39)
- [src/tools/FileWriteTool/UI.tsx:79](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx#L79)
- [src/tools/FileWriteTool/UI.tsx:362](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx#L362)
- [src/tools/FileWriteTool/UI.tsx:376](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx#L376)
- [src/tools/FileWriteTool/UI.tsx:396](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx#L396)

所以你截图里的：

`● Write(helloworld.py)`

和

`Wrote 1 lines to helloworld.py`

都属于客户端对工具调用/结果的渲染，不是模型最终自然语言回复本身。

---

## 12. 为什么还会再来一句 `已创建 helloworld.py。`

这就是第二轮模型回复。

### 12.1 工具结果会被加入下一轮消息历史

`query.ts` 在拿到 tool result 后，会把这些结果追加到 `toolResults`：

- [src/query.ts:1384](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L1384)
- [src/query.ts:1395](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L1395)

然后在准备“下一轮”时，把消息状态更新为：

`messages = [...messagesForQuery, ...assistantMessages, ...toolResults]`

源码：

- [src/query.ts:1714](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L1714)
- [src/query.ts:1715](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L1715)
- [src/query.ts:1716](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L1716)
- [src/query.ts:1727](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts#L1727)

这里要注意一个实现细节：

- 逻辑上看，这是“第二轮模型请求”
- 实现上并不是 UI 再触发一次 `onSubmit`
- 而是 `queryLoop` 在内部继续 while 循环，进入下一轮状态

也就是说，这是一种“同一次 turn 内的工具回环”，不是用户又提交了一次输入。

### 12.2 第二轮模型读到 tool_result 后，输出自然语言答复

因为上一轮的 `tool_result` 已经告诉模型：

`File created successfully at: helloworld.py`

所以第二轮模型就会顺势生成一句自然语言总结，例如你看到的：

`已创建 helloworld.py。`

这句中文不是客户端写死的模板，而是第二轮模型自己生成的内容。

换句话说：

- `Write(...)` 是模型决定的工具调用
- `Wrote 1 lines ...` 是客户端渲染的工具结果卡片
- `已创建 helloworld.py。` 是模型根据 tool_result 生成的最终回复

这是三层不同的东西。

---

## 13. 用时序图把这次交互串起来

可以把这次真实过程压缩成下面这条线：

1. 你执行 `./bin/claude-haha`
2. `bin/claude-haha` 启动 `src/entrypoints/cli.tsx`
3. `cli.tsx` 导入 `src/main.tsx`
4. `main.tsx` 调用 `launchRepl(...)`
5. `REPL` 渲染 `PromptInput`
6. 你在输入框里输入 `帮我在当前目录下写一个helloworld.py脚本`
7. 你按下 Enter
8. `useTextInput.handleEnter()` 调用 `onSubmit(originalValue)`
9. `REPL.onSubmit(...)` 调用 `handlePromptSubmit(...)`
10. `handlePromptSubmit` 调用 `processUserInput(...)`
11. `processUserInput` 收集 attachment，其中包括 IDE 当前选区
12. `processTextPrompt(...)` 产出 `userMessage + attachmentMessages`
13. `handlePromptSubmit` 调用 `onQuery(...)`
14. `REPL.onQueryImpl(...)` 构造 `toolUseContext + systemPrompt + userContext + systemContext`
15. `query.ts` 发起第一次模型请求
16. 模型输出 `tool_use(name=Write, file_path=helloworld.py, content=...)`
17. UI 实时显示 `Write(helloworld.py)`
18. 工具执行层调用 `FileWriteTool.call(...)`
19. 文件真正写入 `helloworld.py`
20. UI 显示 `Wrote 1 lines to helloworld.py`
21. `tool_result` 被加入消息历史
22. `query.ts` 在内部进入下一轮模型请求
23. 模型读到 `tool_result` 后输出 `已创建 helloworld.py。`

---

## 14. 从学习项目角度，你最应该抓住的几个点

### 14.1 客户端和模型的职责分工非常清晰

客户端负责：

- 捕获输入
- 组织上下文
- 暴露工具 schema
- 执行工具
- 渲染工具调用与工具结果

模型负责：

- 判断要不要用工具
- 决定用哪个工具
- 构造工具参数
- 在工具执行完成后生成自然语言答复

### 14.2 “一次对话”不等于“一次模型回复”

这个项目的核心不是简单 chat completion，而是：

`模型 -> 工具 -> 模型 -> 可能再工具 -> 再模型`

所以你以后看源码时，不要只盯着“用户输入后调用一次 API”。真正的主线应该盯：

- `handlePromptSubmit`
- `processUserInput`
- `onQueryImpl`
- `query.ts`
- `toolExecution.ts`

### 14.3 IDE 上下文注入是这个项目很重要的一层增强

你的截图里那条 Cursor 选区信息，说明这个项目不是只吃“输入框文本”，它还会吸收：

- IDE 当前选中内容
- 打开的文件
- 诊断信息
- MCP 上下文
- memory / CLAUDE.md / git 状态

这也是它比普通聊天界面更像“编码代理”的原因。

---

## 15. 这次交互涉及的关键源码地图

如果你要继续顺着这条链深入，建议按这个顺序读：

1. [bin/claude-haha](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/bin/claude-haha)
2. [src/entrypoints/cli.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/entrypoints/cli.tsx)
3. [src/main.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/main.tsx)
4. [src/replLauncher.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/replLauncher.tsx)
5. [src/screens/REPL.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/screens/REPL.tsx)
6. [src/components/PromptInput/PromptInput.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/PromptInput/PromptInput.tsx)
7. [src/components/TextInput.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/components/TextInput.tsx)
8. [src/hooks/useTextInput.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useTextInput.ts)
9. [src/utils/handlePromptSubmit.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/handlePromptSubmit.ts)
10. [src/utils/processUserInput/processUserInput.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts)
11. [src/utils/processUserInput/processTextPrompt.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processTextPrompt.ts)
12. [src/utils/attachments.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/attachments.ts)
13. [src/hooks/useIdeSelection.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/hooks/useIdeSelection.ts)
14. [src/context.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/context.ts)
15. [src/constants/prompts.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/constants/prompts.ts)
16. [src/utils/systemPrompt.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/systemPrompt.ts)
17. [src/query.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts)
18. [src/utils/messages.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/messages.ts)
19. [src/services/api/claude.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/api/claude.ts)
20. [src/services/tools/toolExecution.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts)
21. [src/tools/FileWriteTool/FileWriteTool.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/FileWriteTool.ts)
22. [src/tools/FileWriteTool/UI.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/tools/FileWriteTool/UI.tsx)

---

## 16. 一句话总结

这次“帮我在当前目录下写一个 helloworld.py 脚本”的执行本质上是：

`输入框捕获 Enter -> REPL 提交 -> processUserInput 组装用户消息和 IDE 附件 -> query 发起第一轮模型请求 -> 模型发出 Write 工具调用 -> FileWriteTool 真正写盘 -> tool_result 回流到消息历史 -> 第二轮模型输出“已创建 helloworld.py。”`

如果你要继续学这个项目，下一步最值得深入的不是 UI，而是把 [src/query.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/query.ts) 和 [src/services/tools/toolExecution.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/services/tools/toolExecution.ts) 这两份文件彻底吃透。它们基本就是这个代理系统的“主循环”和“工具执行内核”。
