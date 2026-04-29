# Claude Code Haha 斜杠命令总览

本文基于仓库里的固定命令注册表 [`src/commands.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts) 整理，目标是帮助你从“命令系统”角度快速理解这个项目。

如果你当前最关心的是“每个 `/` 命令到底干什么”，可以直接跳到第 11 节“逐命令功能说明”。

## 统计范围

- 本文统计的是注册到 slash command 系统里的内置命令，也就是你在 REPL 里输入 `/xxx` 会走到的那批命令。
- 文中对同名命令做了去重。例如 `/context`、`/extra-usage` 在交互/非交互场景各有一套实现，但文档只按一个 slash 名字介绍。
- 运行时动态加载的命令不在本文完整统计范围内：
  - `.claude/skills/` 里的 skills
  - 插件带来的 `/plugin-name:command`
  - workflow / MCP / marketplace 动态注入的命令
- 仓库里还包含一批 Anthropic 内部命令、feature-gated 命令，以及本地版被 stub 掉的占位命令。它们统一放在文末单独说明。

## 命令类型速记

- `local-jsx`
  - 本地直接渲染一个 Ink 界面或对话框，通常不会立刻把命令文本交给模型。
- `local`
  - 本地执行逻辑，返回文本结果或直接改状态。
- `prompt`
  - 命令本身会展开成一段 prompt，再交给 Claude 主循环和工具系统去执行。

## 1. 会话与上下文类命令

| 命令 | 别名 | 类型 | 作用 | 备注 |
| --- | --- | --- | --- | --- |
| `/help` | - | `local-jsx` | 打开帮助与可用命令列表。 | 学习入口。 |
| `/clear` | `/reset`, `/new` | `local` | 清空当前对话，释放 context。 | 相当于新开一轮。 |
| `/compact` | - | `local` | 压缩对话历史，把历史总结后继续保留在上下文里。 | 节省上下文窗口。 |
| `/context` | - | `local-jsx` | 可视化当前上下文使用情况。 | 非交互模式有单独实现。 |
| `/cost` | - | `local` | 查看当前会话的成本与时长。 | 部分订阅场景会隐藏。 |
| `/copy` | - | `local-jsx` | 复制 Claude 最近一次回复到剪贴板。 | 支持拷贝较早回复。 |
| `/rename` | - | `local-jsx` | 重命名当前会话。 | 会影响 `/resume` 列表展示。 |
| `/resume` | `/continue` | `local-jsx` | 恢复之前的会话。 | 支持搜索和选择历史会话。 |
| `/status` | - | `local-jsx` | 查看版本、模型、账号、API 连通性、工具状态等。 | 偏全局状态面板。 |
| `/stats` | - | `local-jsx` | 查看 Claude Code 的使用统计与活跃情况。 | 偏历史分析。 |
| `/tag` | - | `local-jsx` | 给当前会话打一个可搜索标签。 | 便于后续筛选会话。 |
| `/export` | - | `local-jsx` | 导出当前会话到文件或剪贴板。 | 便于归档或分享。 |
| `/rewind` | `/checkpoint` | `local` | 把代码和/或对话回退到某个历史点。 | 带恢复性质。 |
| `/insights` | - | `prompt` | 生成 Claude Code 会话分析报告。 | 由模型读取日志生成。 |
| `/statusline` | - | `prompt` | 帮你设置 Claude Code 的 status line UI。 | 本质是一个 setup 型 prompt 命令。 |
| `/think-back` | - | `local-jsx` | 打开 “Claude Code 年度回顾” 入口。 | 偏彩蛋/总结。 |
| `/thinkback-play` | - | `local` | 播放 thinkback 动画。 | 演示型命令。 |
| `/exit` | `/quit` | `local-jsx` | 退出当前 REPL。 | `immediate` 命令。 |

## 2. 配置、模型与权限类命令

| 命令 | 别名 | 类型 | 作用 | 备注 |
| --- | --- | --- | --- | --- |
| `/config` | `/settings` | `local-jsx` | 打开配置面板。 | 最常用的设置入口。 |
| `/add-dir` | - | `local-jsx` | 添加额外工作目录。 | 扩大当前会话可访问目录范围。 |
| `/agents` | - | `local-jsx` | 管理 agent 配置。 | 对应自定义 agent 定义。 |
| `/advisor` | - | `local` | 配置 advisor model。 | 带参数时可启用/关闭 advisor。 |
| `/brief` | - | `local-jsx` | 切换 brief-only 模式。 | 更偏简洁交互。 |
| `/color` | - | `local-jsx` | 设置当前会话的 prompt bar 颜色。 | 视觉定制。 |
| `/effort` | - | `local-jsx` | 设置模型 effort level。 | 常见值如 `low / medium / high / max`。 |
| `/fast` | - | `local-jsx` | 切换 fast mode。 | 仅在支持的模型/账户场景有效。 |
| `/hooks` | - | `local-jsx` | 查看并管理 hook 配置。 | 对应工具事件钩子。 |
| `/keybindings` | - | `local` | 打开或创建 keybindings 配置文件。 | 定制快捷键。 |
| `/memory` | - | `local-jsx` | 编辑 Claude memory 文件。 | 管理记忆类上下文。 |
| `/model` | - | `local-jsx` | 切换 Claude Code 当前使用的模型。 | REPL 中常用。 |
| `/output-style` | - | `local-jsx` | 旧版输出风格设置。 | 已废弃，推荐用 `/config`。 |
| `/permissions` | `/allowed-tools` | `local-jsx` | 管理 allow / ask / deny 规则与工作目录白名单。 | 对应权限规则编辑器。 |
| `/plan` | - | `local-jsx` | 进入 plan mode，或查看当前 session plan。 | 规划优先工作流。 |
| `/privacy-settings` | - | `local-jsx` | 查看并修改隐私设置。 | 与数据/隐私偏好有关。 |
| `/sandbox` | - | `local-jsx` | 查看或配置 sandbox 状态。 | 平台/策略不支持时会隐藏。 |
| `/skills` | - | `local-jsx` | 列出当前可用 skills。 | 只看固定技能入口，不含所有动态细节。 |
| `/theme` | - | `local-jsx` | 切换主题。 | UI 定制。 |
| `/vim` | - | `local` | 在 Vim / Normal 编辑模式之间切换。 | 输入体验相关。 |

## 3. 开发、审查与自动化类命令

| 命令 | 别名 | 类型 | 作用 | 备注 |
| --- | --- | --- | --- | --- |
| `/branch` | `/fork` | `local-jsx` | 从当前对话分叉出一个新分支。 | `fork` 只是兼容别名；当独立 `/fork` 存在时可能不生效。 |
| `/btw` | - | `local-jsx` | 在不中断主对话的前提下提一个侧边问题。 | `immediate` 命令。 |
| `/diff` | - | `local-jsx` | 查看未提交改动和按 turn 的 diff。 | 代码审阅常用。 |
| `/doctor` | - | `local-jsx` | 诊断并验证 Claude Code 安装与配置。 | 偏排障。 |
| `/feedback` | `/bug` | `local-jsx` | 提交 Claude Code 反馈。 | 别名偏“报 bug”。 |
| `/files` | - | `local` | 列出当前上下文里已经带进来的文件。 | 看模型现在“看到了什么”。 |
| `/init` | - | `prompt` | 初始化 CLAUDE.md，并可选创建 skills / hooks。 | 项目上手命令。 |
| `/pr-comments` | - | `prompt` | 获取并整理 GitHub PR 评论。 | 更像兼容/迁移命令，和插件生态有关。 |
| `/review` | - | `prompt` | 对 PR 做本地代码审查。 | 侧重 diff 分析。 |
| `/security-review` | - | `prompt` | 对当前分支改动做安全审查。 | 偏安全漏洞视角。 |
| `/tasks` | `/bashes` | `local-jsx` | 管理后台任务。 | 例如长时间 Bash / 子任务。 |
| `/ultrareview` | - | `local-jsx` | 走 Claude Code on the web 的深度 bug review 流程。 | 条件开启，时间更长。 |

## 4. 集成、远程与生态类命令

| 命令 | 别名 | 类型 | 作用 | 备注 |
| --- | --- | --- | --- | --- |
| `/chrome` | - | `local-jsx` | Claude in Chrome 设置入口。 | 依赖 `claude-ai` 订阅能力。 |
| `/desktop` | `/app` | `local-jsx` | 在 Claude Desktop 里继续当前会话。 | Claude.ai 相关能力。 |
| `/ide` | - | `local-jsx` | 管理 IDE 集成并查看连接状态。 | 和编辑器桥接有关。 |
| `/install-github-app` | - | `local-jsx` | 为仓库配置 Claude GitHub Actions。 | GitHub 集成入口。 |
| `/install-slack-app` | - | `local` | 安装 Claude Slack App。 | 依赖账号能力。 |
| `/mcp` | - | `local-jsx` | 管理 MCP 服务器。 | 项目扩展体系核心入口。 |
| `/mobile` | `/ios`, `/android` | `local-jsx` | 展示移动端下载二维码。 | 偏安装引导。 |
| `/plugin` | `/plugins`, `/marketplace` | `local-jsx` | 管理 Claude Code 插件。 | `immediate`，也是 marketplace 入口。 |
| `/reload-plugins` | - | `local` | 让当前 session 重新加载插件变化。 | 激活新装/修改后的插件。 |
| `/remote-control` | `/rc` | `local-jsx` | 把当前终端连接成 remote-control session。 | 桥接/远控入口，`immediate`。 |
| `/remote-env` | - | `local-jsx` | 配置 teleport/remote session 的默认远程环境。 | 远程运行相关。 |
| `/session` | `/remote` | `local-jsx` | 查看 remote session URL 和二维码。 | 只在 remote mode 下显示。 |
| `/terminal-setup` | - | `local-jsx` | 配置终端换行/键位支持。 | 例如 Option+Enter / Shift+Enter。 |
| `/voice` | - | `local` | 切换 voice mode。 | 依赖账户和 feature。 |
| `/web-setup` | - | `local-jsx` | 配置 Claude Code on the web。 | 依赖 GitHub 账号接入与 `claude-ai`。 |

## 5. 账号、订阅与周边类命令

| 命令 | 别名 | 类型 | 作用 | 备注 |
| --- | --- | --- | --- | --- |
| `/extra-usage` | - | `local-jsx` | 配置 extra usage，避免额度打满后完全停用。 | 有交互版和非交互版实现。 |
| `/login` | - | `local-jsx` | 登录或切换 Anthropic 账号。 | 文案会根据当前登录状态变化。 |
| `/logout` | - | `local-jsx` | 登出 Anthropic 账号。 | 账号管理。 |
| `/passes` | - | `local-jsx` | 分享 Claude Code 试用周/邀请权益。 | 是否显示取决于资格缓存。 |
| `/release-notes` | - | `local` | 查看更新说明。 | 偏版本信息。 |
| `/upgrade` | - | `local-jsx` | 升级到更高套餐。 | 面向 `claude-ai`。 |
| `/usage` | - | `local-jsx` | 查看套餐使用额度。 | 面向 `claude-ai`。 |
| `/stickers` | - | `local` | 订购 Claude Code 贴纸。 | 周边类命令。 |

## 6. 隐藏或调试型公开命令

这些命令在注册表里存在，但通常不会直接出现在帮助列表里，或只在特定时机出现。

| 命令 | 类型 | 作用 | 备注 |
| --- | --- | --- | --- |
| `/heapdump` | `local` | 把 JS heap dump 到 `~/Desktop`。 | `isHidden: true`，偏诊断调试。 |
| `/rate-limit-options` | `local-jsx` | 在触发 rate limit 时显示后续选项。 | `isHidden: true`，更多是系统内部流程入口。 |

## 7. 条件/Feature-Gated 命令

这些命令在 [`src/commands.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts) 里被引用，但当前本地仓库缺少对应实现文件，或只有 feature 打开时才会真正加入命令表。下面名称大多根据变量名或路径推断。

| 推定命令 | 来源变量/路径 | 状态 | 说明 |
| --- | --- | --- | --- |
| `/assistant` | `assistantCommand` / `commands/assistant` | 缺实现 | 推测用于 assistant mode 相关交互。 |
| `/buddy` | `buddy` / `commands/buddy` | 缺实现 | 推测用于 companion/buddy 功能。 |
| `/fork` | `forkCmd` / `commands/fork` | 缺实现 | 注意它和 `/branch` 的 `fork` 兼容别名不是一回事。 |
| `/peers` | `peersCmd` / `commands/peers` | 缺实现 | 可能与 UDS inbox / peer session 有关。 |
| `/proactive` | `proactive` / `commands/proactive` | 缺实现 | 推测用于 proactive/autonomous 模式。 |
| `/remote-control-server` | `remoteControlServerCommand` | 缺实现 | 可能是 remote-control 服务端调试入口。 |
| `/torch` | `torch` / `commands/torch` | 缺实现 | 仅在 feature 打开时引用。 |
| `/workflows` | `workflowsCmd` / `commands/workflows` | 缺实现 | 推测用于 workflow scripts。 |

## 8. 内部 / Anthropic-Only / 本地版占位命令

这一部分是“项目源码里挂着，但公开本地版不一定能正常使用”的命令。

### 8.1 有实际实现的内部命令

| 命令 | 类型 | 作用 | 备注 |
| --- | --- | --- | --- |
| `/commit` | `prompt` | 自动分析改动并创建一个 git commit。 | 允许模型调用受限 git/bash 工具。 |
| `/commit-push-pr` | `prompt` | 自动提交、推送并创建 PR。 | 也是 prompt 驱动。 |
| `/init-verifiers` | `prompt` | 创建 verifier skill，用于自动验证代码改动。 | 偏 Anthropic 内部工作流。 |
| `/bridge-kick` | `local` | 注入桥接失败状态，测试恢复流程。 | 明显是调试命令。 |
| `/version` | `local` | 打印当前 session 实际运行版本。 | 和 autoupdate 下载版本区分。 |
| `/ultraplan` | `local-jsx` | 启动 Claude Code on the web 的高级规划流程。 | 内部/实验味很重。 |

### 8.2 在本地版中被 stub 掉的内部命令

这些文件在当前仓库里基本都是：

```js
export default { isEnabled: () => false, isHidden: true, name: 'stub' }
```

也就是说“注册表里保留了位置，但本地版实际上不可用”。

| 推定命令 | 当前状态 | 备注 |
| --- | --- | --- |
| `/ant-trace` | stub | 内部诊断命令。 |
| `/autofix-pr` | stub | PR 自动修复相关。 |
| `/backfill-sessions` | stub | 会话数据回填相关。 |
| `/break-cache` | stub | 破坏/重置缓存的调试命令。 |
| `/bughunter` | stub | 深度找 bug 的内部流程。 |
| `/ctx_viz` | stub | 上下文可视化实验命令。 |
| `/debug-tool-call` | stub | 工具调用调试。 |
| `/env` | stub | 环境查看/导出相关。 |
| `/good-claude` | stub | 内部实验命令。 |
| `/issue` | stub | 报 issue / 反馈流程相关。 |
| `/mock-limits` | stub | 配额/限制模拟。 |
| `/oauth-refresh` | stub | OAuth 刷新调试。 |
| `/onboarding` | stub | onboarding 流程入口。 |
| `/perf-issue` | stub | 性能问题上报。 |
| `/reset-limits` | stub | 重置配额限制。 |
| `/share` | stub | 分享/传播相关内部入口。 |
| `/summary` | stub | 摘要类内部入口。 |
| `/teleport` | stub | teleport 流程在本地版被占位。 |

### 8.3 注册表里还引用、但当前仓库缺文件的内部命令

| 推定命令 | 状态 | 备注 |
| --- | --- | --- |
| `/force-snip` | 缺文件 | 与 `HISTORY_SNIP` 相关。 |
| `/subscribe-pr` | 缺文件 | 可能用于 PR 活动订阅。 |
| `/agents-platform` | 缺文件 | `agentsPlatform` 变量存在，但当前树中无实现。 |

## 9. 阅读这套命令系统，建议优先看的源码

如果你要继续深入 slash command 机制，推荐按下面顺序读：

1. [`src/commands.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)
   - 看所有命令是怎么注册进总表的。
2. [`src/types/command.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/types/command.ts)
   - 看 `local` / `local-jsx` / `prompt` 三种命令抽象。
3. [`src/utils/processUserInput/processUserInput.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processUserInput.ts)
   - 看 slash command 和普通文本输入是如何分流的。
4. [`src/utils/processUserInput/processSlashCommand.tsx`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/utils/processUserInput/processSlashCommand.tsx)
   - 看 `/xxx` 命令实际如何执行、怎样生成消息。
5. 任选一个命令入口文件，比如：
   - [`src/commands/permissions/index.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/permissions/index.ts)
   - [`src/commands/review.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/review.ts)
   - [`src/commands/mcp/index.ts`](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/mcp/index.ts)

## 10. 一句话理解

这套项目里的 `/` 命令并不只是“文本宏替换”，而是一个完整的命令系统：

- 有的命令本地弹 UI
- 有的命令本地改状态
- 有的命令会展开成 prompt 再交给模型
- 还有一部分命令会桥接到 MCP、插件、远程控制和 web 端流程

如果你把这份文档配合 `commands.ts + types/command.ts + processSlashCommand.tsx` 一起读，基本就能把该项目的 slash command 体系吃透。

## 11. 逐命令功能说明

这一节把“公开可见或条件可见”的 slash 命令逐条展开。阅读时请注意三件事：

- 不是每个命令都会在你本地看到。很多命令还会再经过 `availability`、`isEnabled()`、feature flag、账号类型、远程模式等条件过滤。
- 同一个 slash 名字有时会在交互模式和非交互模式对应两套实现，例如 `/context`、`/extra-usage`。下面按“用户看到的命令名”来讲，不重复展开。
- `local-jsx` 表示命令先在本地渲染 Ink 界面，`local` 表示本地直接执行，`prompt` 表示命令会生成一段 prompt 再进入 Claude 主循环。

### 11.1 会话与上下文类命令

#### `/help`
功能：打开帮助面板，列出当前会话此刻真正可用的 slash 命令。它不仅是“命令列表”，也是查看哪些条件命令已经生效的最快入口。  
输入：无参数。  
执行方式：`local-jsx`，直接渲染本地帮助 UI，不走模型。  
源码：[src/commands/help/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/help/index.ts)

#### `/clear` `/reset` `/new`
功能：清空当前会话历史并释放上下文，相当于从一个新的聊天线程重新开始。它不会保留总结；如果你想“压缩后继续聊”，应该用 `/compact`。  
输入：无参数；`/reset`、`/new` 都是别名。  
执行方式：`local`，本地直接改会话状态；非交互模式不支持。  
源码：[src/commands/clear/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/clear/index.ts)

#### `/compact`
功能：把当前长对话压缩成一段总结，再带着总结继续聊，用来节省 context window。它是“保留语义、缩短历史”的命令。  
输入：支持可选补充说明，例如你可以要求它在压缩时更保留决策过程或待办项。  
执行方式：`local`；支持非交互模式。  
源码：[src/commands/compact/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/compact/index.ts)

#### `/context`
功能：查看当前上下文使用情况。交互模式下它会渲染彩色网格或可视化界面；非交互模式下会退化成更直接的文本输出。  
输入：无参数。  
执行方式：交互模式是 `local-jsx`，非交互模式是 `local`。  
源码：[src/commands/context/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/context/index.ts)

#### `/cost`
功能：显示当前 session 到现在为止的成本与持续时间，适合观察一次长任务到底花了多少钱、跑了多久。  
输入：无参数。  
执行方式：`local`；支持非交互模式。对普通 Claude.ai 订阅用户通常会隐藏，但对内部用户会保留。  
源码：[src/commands/cost/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/cost/index.ts)

#### `/copy`
功能：复制 Claude 最近一次回复；如果回复里含多个代码块，还可以在选择器里只复制某一个代码块。`/copy N` 可以拿到倒数第 N 条有效 assistant 回复。  
输入：可写一个数字，例如 `/copy 3`。  
执行方式：`local-jsx`。它会优先走剪贴板，同时把内容写到临时文件作为兜底，所以不是单纯的“复制字符串”。  
源码：[src/commands/copy/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/copy/index.ts)

#### `/rename`
功能：重命名当前会话。这个名字会影响后面 `/resume`、历史搜索、会话列表里的展示。  
输入：可选新名字；没有参数时通常会进入交互式改名流程。  
执行方式：`local-jsx`。  
源码：[src/commands/rename/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/rename/index.ts)

#### `/resume` `/continue`
功能：恢复过去的会话。你既可以传 conversation id，也可以传搜索词，让系统去筛历史对话。  
输入：`[conversation id or search term]`；别名是 `/continue`。  
执行方式：`local-jsx`，通常会打开选择/搜索式 UI。  
源码：[src/commands/resume/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/resume/index.ts)

#### `/status`
功能：打开全局状态面板，集中查看 Claude Code 版本、当前模型、账号登录状态、API 连通性、工具状态等。排查“为什么今天不好用”时很常用。  
输入：无参数。  
执行方式：`local-jsx`，而且是 `immediate` 命令，所以会比较快地直接弹状态页。  
源码：[src/commands/status/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/status/index.ts)

#### `/stats`
功能：显示你的 Claude Code 使用统计和活跃情况，更偏“历史回顾”和“使用画像”，不是只看当前这一轮。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/stats/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/stats/index.ts)

#### `/tag`
功能：给当前会话切换一个可搜索标签，方便后面按标签找回会话。它不是普通注释，而是会话检索维度。  
输入：`<tag-name>`。  
执行方式：`local-jsx`；当前代码里只对 `USER_TYPE === 'ant'` 开启。  
源码：[src/commands/tag/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/tag/index.ts)

#### `/export`
功能：导出当前会话内容到文件或剪贴板。无参数时会弹导出对话框，并自动根据第一条用户消息生成默认文件名；带文件名时会直接在当前工作目录写出 `.txt` 文件。  
输入：`[filename]`。  
执行方式：`local-jsx`。它会先把消息和工具输出渲染成纯文本，再执行导出。  
源码：[src/commands/export/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/export/index.ts)

#### `/rewind` `/checkpoint`
功能：把代码和/或对话回退到某个历史点，是一种“回到过去重新走”的能力。名字虽然像 git checkpoint，但它管的是 Claude Code 自己的会话/工作流检查点。  
输入：无固定参数格式，主要依赖后续交互流程；别名是 `/checkpoint`。  
执行方式：`local`；非交互模式不支持。  
源码：[src/commands/rewind/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/rewind/index.ts)

#### `/insights`
功能：分析 Claude Code 的 session 日志并生成报告，属于“读历史日志后再总结”的命令。它不是简单统计，而是会用模型对会话做分析。  
输入：通常无参数。  
执行方式：`prompt`。对应实现文件很大，而且是懒加载，只有真正触发 `/insights` 才会去加载分析逻辑。  
源码：[src/commands/insights.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/insights.ts)

#### `/statusline`
功能：帮你配置 Claude Code 的 status line UI。它会把你的需求包装成一个 `statusline-setup` 子 agent 任务，默认会参考 shell 的 `PS1` 配置来生成方案。  
输入：可写自然语言需求；不写时默认 prompt 是“根据我的 shell PS1 配置来设置 statusLine”。  
执行方式：`prompt`，允许读取主目录文件并编辑 `~/.claude/settings.json`；非交互模式禁用。  
源码：[src/commands/statusline.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/statusline.tsx)

#### `/think-back`
功能：打开 “Claude Code Year in Review” 入口，更像年度回顾/彩蛋式功能，而不是开发命令。  
输入：无参数。  
执行方式：`local-jsx`；由 growthbook gate `tengu_thinkback` 控制是否显示。  
源码：[src/commands/thinkback/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/thinkback/index.ts)

#### `/thinkback-play`
功能：直接播放 thinkback 动画，是 `/think-back` 之后更偏演示或播放层的命令。  
输入：无参数。  
执行方式：`local`。  
源码：[src/commands/thinkback-play/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/thinkback-play/index.ts)

#### `/exit` `/quit`
功能：退出当前 REPL。和 `/clear` 不同，它不是开新会话，而是直接离开当前 Claude Code 终端交互。  
输入：无参数；别名是 `/quit`。  
执行方式：`local-jsx` 且 `immediate`。  
源码：[src/commands/exit/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/exit/index.ts)

### 11.2 配置、模型与权限类命令

#### `/config` `/settings`
功能：打开总配置面板，是很多设置项的统一入口。像输出风格、偏好、一些账号/界面设置，最后都会在这里汇总。  
输入：无参数；`/settings` 是别名。  
执行方式：`local-jsx`。  
源码：[src/commands/config/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/config/index.ts)

#### `/add-dir`
功能：把新的工作目录加入当前会话，使 Claude Code 可以在该目录下读写/浏览文件。它解决的是“当前会话只看得到一个目录，但我还想把另一个仓库或子目录也纳入工作范围”。  
输入：`<path>`。  
执行方式：`local-jsx`。  
源码：[src/commands/add-dir/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/add-dir/index.ts)

#### `/agents`
功能：管理 agent 配置。这里的重点不是“运行某个 agent”，而是查看或编辑 Claude Code 里定义好的 agent 方案。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/agents/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/agents/index.ts)

#### `/advisor`
功能：配置 advisor model。`/advisor` 不带参数时会显示当前 advisor 状态；`/advisor <model>` 可以设置；`/advisor off` 或 `/advisor unset` 可以关闭。  
输入：`[<model>|off]`。  
执行方式：`local`；支持非交互模式。只有账号/模型能力允许配置 advisor 时才会显示。  
源码：[src/commands/advisor.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/advisor.ts)

#### `/brief`
功能：切换 brief-only mode。打开后，系统会更强地要求通过 brief tool 产出面向用户的简短回复，而不是普通长文本。  
输入：无参数。  
执行方式：`local-jsx` 且 `immediate`。它完全受 `KAIROS` / `KAIROS_BRIEF` 特性和 entitlement 控制，所以很多环境里看不到。  
源码：[src/commands/brief.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/brief.ts)

#### `/color`
功能：设置当前会话 prompt bar 的颜色，用于视觉区分不同任务或会话。  
输入：`<color|default>`。  
执行方式：`local-jsx` 且 `immediate`。  
源码：[src/commands/color/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/color/index.ts)

#### `/effort`
功能：设置模型推理 effort level，用来控制回答速度和思考深度之间的权衡。  
输入：`[low|medium|high|max|auto]`。  
执行方式：`local-jsx`。  
源码：[src/commands/effort/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/effort/index.ts)

#### `/fast`
功能：切换 fast mode。它通常只在特定模型和账号套餐下可用，本质上是把主模型切到更快的一档。  
输入：`[on|off]`。  
执行方式：`local-jsx`；有 `availability` 限制，而且只有 `isFastModeEnabled()` 为真时才会出现在命令列表。  
源码：[src/commands/fast/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/fast/index.ts)

#### `/hooks`
功能：查看并管理 hook 配置，也就是 Claude Code 在工具事件前后自动执行的那些钩子。它是研究“为什么每次编辑后都会自动格式化/跑命令”的入口。  
输入：无参数。  
执行方式：`local-jsx` 且 `immediate`。  
源码：[src/commands/hooks/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/hooks/index.ts)

#### `/keybindings`
功能：打开或创建快捷键配置文件，让你自定义 REPL 里的按键行为。  
输入：无参数。  
执行方式：`local`；只在 keybinding customization 能力打开时可用。  
源码：[src/commands/keybindings/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/keybindings/index.ts)

#### `/memory`
功能：编辑 Claude memory 文件。这个命令对应的是长期记忆或偏好文件，不是一次性消息上下文。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/memory/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/memory/index.ts)

#### `/model`
功能：切换 Claude Code 当前使用的主模型。命令描述里会动态带出“当前正在用哪个模型”。  
输入：`[model]`。  
执行方式：`local-jsx`；在某些环境下会被标记为 `immediate`。  
源码：[src/commands/model/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/model/index.ts)

#### `/output-style`
功能：旧版输出风格设置入口。源码里已经明确标成 deprecated，官方推荐直接用 `/config`。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/output-style/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/output-style/index.ts)

#### `/permissions` `/allowed-tools`
功能：管理工具权限规则，包括 allow、deny 等策略。打开界面后还能对历史被拒绝的命令做 retry，因此它不只是“看规则”，还是权限修正入口。  
输入：无参数；别名是 `/allowed-tools`。  
执行方式：`local-jsx`，底层会渲染 `PermissionRuleList` 组件。  
源码：[src/commands/permissions/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/permissions/index.ts)、[src/commands/permissions/permissions.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/permissions/permissions.tsx)

#### `/plan`
功能：进入 plan mode，或者在已经处于 plan mode 时查看当前计划。`/plan open` 会把 plan 文件直接交给外部编辑器打开；`/plan <description>` 则是在开启 plan mode 后继续把这段描述当成后续 query。  
输入：`[open|<description>]`。  
执行方式：`local-jsx`。它不只是展示 UI，还会修改 `toolPermissionContext.mode`，并准备 plan mode 所需的权限上下文。  
源码：[src/commands/plan/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/plan/index.ts)、[src/commands/plan/plan.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/plan/plan.tsx)

#### `/privacy-settings`
功能：查看并修改隐私设置。它主要面向 consumer subscriber，所以不是所有账户类型都会看到。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/privacy-settings/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/privacy-settings/index.ts)

#### `/sandbox`
功能：查看或配置 sandbox 状态，包括是否开启 sandbox、是否 auto-allow、是否允许 unsandboxed fallback，以及对某些命令模式做排除。  
输入：`exclude "command pattern"` 这种排除模式。  
执行方式：`local-jsx` 且 `immediate`。只有当前平台和策略支持 sandbox 时才会显示。  
源码：[src/commands/sandbox-toggle/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/sandbox-toggle/index.ts)

#### `/skills`
功能：列出当前可用的 skills。这里能看到的不只是固定内置 skill，也可能包含项目目录、插件、运行期加载出来的 skill 命令。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/skills/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/skills/index.ts)

#### `/theme`
功能：切换 Claude Code 主题。它影响的是终端 UI 呈现，不是模型输出内容。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/theme/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/theme/index.ts)

#### `/vim`
功能：在 Vim 编辑模式和 Normal 编辑模式之间切换，影响的是输入框键位行为。  
输入：无参数。  
执行方式：`local`；非交互模式不支持。  
源码：[src/commands/vim/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/vim/index.ts)

### 11.3 开发、审查与自动化类命令

#### `/branch`
功能：从当前对话点位分叉出一个新分支，让你在不污染主会话的情况下继续探索另一条思路。它处理的是“会话分支”，不是 git branch 本身。  
输入：`[name]`，可以给这条分叉起名。  
执行方式：`local-jsx`。当独立的 `/fork` 命令不存在时，它会临时把 `fork` 当兼容别名。  
源码：[src/commands/branch/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/branch/index.ts)

#### `/btw`
功能：在不中断当前主任务的前提下，快速提一个侧边问题。它更像“顺带问一句”，适合临时确认概念或背景信息。  
输入：`<question>`。  
执行方式：`local-jsx` 且 `immediate`。  
源码：[src/commands/btw/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/btw/index.ts)

#### `/diff`
功能：查看当前工作区未提交的改动，以及按 turn 归档的 diff。对“Claude 这一步到底改了什么”非常有帮助。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/diff/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/diff/index.ts)

#### `/doctor`
功能：诊断并验证 Claude Code 的安装和配置，适合排查启动异常、依赖缺失、配置错误、权限问题。  
输入：无参数。  
执行方式：`local-jsx`。如果环境变量显式禁用了 doctor 命令，它就不会显示。  
源码：[src/commands/doctor/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/doctor/index.ts)

#### `/feedback` `/bug`
功能：提交关于 Claude Code 的反馈；当你把它当 `/bug` 用时，语义就是“这是问题上报”。  
输入：`[report]`。  
执行方式：`local-jsx`。  
源码：[src/commands/feedback/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/feedback/index.ts)

#### `/files`
功能：列出当前已经被带进上下文的文件，让你知道模型“现在看到的是哪些文件”，而不是整个仓库。  
输入：无参数。  
执行方式：`local`；支持非交互模式。当前代码里只对 `USER_TYPE === 'ant'` 开启。  
源码：[src/commands/files/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/files/index.ts)

#### `/init`
功能：初始化 CLAUDE.md。新版本流程不只会建项目级 CLAUDE.md，还可能顺带询问是否创建 `CLAUDE.local.md`、skills、hooks；旧版本则主要是生成一份项目说明文件。  
输入：通常不需要参数。  
执行方式：`prompt`。它会先分析代码库，再可能发起询问、生成文档、建议优化项。  
源码：[src/commands/init.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/init.ts)

#### `/pr-comments`
功能：获取并整理 GitHub PR 评论。当前实现本质上是“命令已迁到插件”，如果 marketplace 还没公开，则会回退到一个 prompt，让 Claude 用 `gh` 和 GitHub API 自行拉取评论并格式化。  
输入：可跟额外补充说明。  
执行方式：`prompt`。  
源码：[src/commands/pr_comments/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/pr_comments/index.ts)

#### `/review`
功能：做本地 PR code review。实现里的默认 prompt 会先用 `gh pr list` 或 `gh pr view` 找 PR，再读 `gh pr diff` 产出审查意见。  
输入：通常是 PR 编号；如果不写，流程会先列出可审的 PR。  
执行方式：`prompt`。它是本地 review 路径，不会自动转去 web。  
源码：[src/commands/review.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/review.ts)

#### `/security-review`
功能：对当前分支相对 `origin/HEAD` 的改动做“只关注安全问题”的审查。它明确要求减少误报，并围绕注入、鉴权、数据泄露等风险输出高置信度发现。  
输入：一般无参数。  
执行方式：`prompt`。和 `/pr-comments` 类似，它现在也是“迁到插件但保留兼容入口”的模式。  
源码：[src/commands/security-review.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/security-review.ts)

#### `/tasks` `/bashes`
功能：打开后台任务管理界面。凡是长时间运行的 Bash、后台任务、异步子流程，都可以在这里查看和管理。  
输入：无参数；别名是 `/bashes`。  
执行方式：`local-jsx`。  
源码：[src/commands/tasks/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/tasks/index.ts)

#### `/ultrareview`
功能：进入 Claude Code on the web 的深度 bug review 流程。它和 `/review` 的区别在于：`/review` 走本地 prompt 审查，而 `/ultrareview` 是一个更慢、更重、更偏发现缺陷和验证问题的 web 流程。  
输入：一般无参数。  
执行方式：`local-jsx`。它只在 growthbook 配置允许时才会显示。  
源码：[src/commands/review.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/review.ts)、[src/commands/review/ultrareviewCommand.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/review/ultrareviewCommand.tsx)

### 11.4 集成、远程与生态类命令

#### `/chrome`
功能：打开 Claude in Chrome 的设置入口。它更接近产品集成配置，而不是代码仓库级功能。  
输入：无参数。  
执行方式：`local-jsx`。只对 `claude-ai` 账户开放，而且非交互模式不显示。  
源码：[src/commands/chrome/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/chrome/index.ts)

#### `/desktop` `/app`
功能：把当前 session 继续到 Claude Desktop。适合你想从终端切到桌面端继续同一上下文时使用。  
输入：无参数；别名是 `/app`。  
执行方式：`local-jsx`。仅对受支持平台开放，并且要求 `claude-ai` 账户。  
源码：[src/commands/desktop/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/desktop/index.ts)

#### `/ide`
功能：管理 IDE 集成并显示连接状态。它是理解“Claude Code 与编辑器怎么桥接”的一个关键入口。  
输入：`[open]`，通常可用于直接打开相关连接或入口。  
执行方式：`local-jsx`。  
源码：[src/commands/ide/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/ide/index.ts)

#### `/install-github-app`
功能：为仓库配置 Claude GitHub Actions。它解决的是“让 Claude 能更自然地进入 GitHub 工作流”的集成问题。  
输入：无参数。  
执行方式：`local-jsx`。对 `claude-ai` 和 `console` 两类账户都开放。  
源码：[src/commands/install-github-app/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/install-github-app/index.ts)

#### `/install-slack-app`
功能：安装 Claude Slack App，是 Slack 生态集成入口。  
输入：无参数。  
执行方式：`local`；只对 `claude-ai` 账户开放，非交互模式不支持。  
源码：[src/commands/install-slack-app/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/install-slack-app/index.ts)

#### `/mcp`
功能：管理 MCP servers，是项目扩展体系里非常重要的一个入口。基础 `/mcp` 会打开管理界面；`/mcp enable xxx`、`/mcp disable xxx` 可直接切换服务状态；`/mcp reconnect xxx` 可重连单个服务。  
输入：`[enable|disable [server-name]]`，以及实现里额外支持的 `reconnect <server-name>`。  
执行方式：`local-jsx` 且 `immediate`。  
源码：[src/commands/mcp/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/mcp/index.ts)、[src/commands/mcp/mcp.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/mcp/mcp.tsx)

#### `/mobile` `/ios` `/android`
功能：展示移动端下载二维码，让你把 Claude 生态扩展到手机端。  
输入：无参数；`/ios`、`/android` 都只是别名，不代表两套不同逻辑。  
执行方式：`local-jsx`。  
源码：[src/commands/mobile/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/mobile/index.ts)

#### `/plugin` `/plugins` `/marketplace`
功能：管理 Claude Code 插件，包括查看 marketplace、安装、启用、停用、查看已装插件等。由于这个项目支持插件命令动态注入，所以 `/plugin` 是理解“命令系统如何扩展”的关键命令。  
输入：无参数。  
执行方式：`local-jsx` 且 `immediate`。  
源码：[src/commands/plugin/index.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/plugin/index.tsx)

#### `/reload-plugins`
功能：重新加载当前 session 里的插件变化。典型场景是你刚装了插件、改了插件文件，想立即生效而不重启 Claude Code。  
输入：无参数。  
执行方式：`local`；非交互模式不支持。  
源码：[src/commands/reload-plugins/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/reload-plugins/index.ts)

#### `/remote-control` `/rc`
功能：把当前终端接成一个 remote-control session，可以理解为“把这个终端暴露成可远程桥接的控制端”。  
输入：`[name]`，可选地给这个 remote-control session 起名。  
执行方式：`local-jsx` 且 `immediate`。它依赖 `BRIDGE_MODE` feature 和 `isBridgeEnabled()`，所以很多本地环境不会显示。  
源码：[src/commands/bridge/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/bridge/index.ts)

#### `/remote-env`
功能：配置 teleport/remote session 默认使用的远程环境。它解决的是“远程会话应该落到哪个环境模板或运行环境”这个问题。  
输入：无参数。  
执行方式：`local-jsx`。需要 `claude-ai` 订阅且策略允许远程 session。  
源码：[src/commands/remote-env/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/remote-env/index.ts)

#### `/session` `/remote`
功能：在已经处于 remote mode 时，显示当前 remote session 的 URL 和二维码。它不是“创建远程会话”，而是“查看当前远程会话入口”。  
输入：无参数；别名是 `/remote`。  
执行方式：`local-jsx`。只有 `getIsRemoteMode()` 为真时才显示。  
源码：[src/commands/session/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/session/index.ts)

#### `/terminal-setup`
功能：配置终端里的换行和键位支持。普通终端上它通常负责安装 Shift+Enter 新行支持；Apple Terminal 下则是 Option+Enter 与 visual bell 相关设置。  
输入：无参数。  
执行方式：`local-jsx`。如果当前终端已经原生支持 CSI u / Kitty keyboard protocol，就会隐藏。  
源码：[src/commands/terminalSetup/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/terminalSetup/index.ts)

#### `/voice`
功能：切换 voice mode，是语音交互入口。  
输入：无参数。  
执行方式：`local`；只对 `claude-ai` 账户开放，而且既要 growthbook 开启，也要 voice mode 真正可用。  
源码：[src/commands/voice/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/voice/index.ts)

#### `/web-setup`
功能：配置 Claude Code on the web。它通常要求先接入 GitHub 账号，再允许把本地能力延伸到 web 端。  
输入：无参数。  
执行方式：`local-jsx`。只对 `claude-ai` 账户开放，且需要远程 session 策略允许、feature gate 打开。  
源码：[src/commands/remote-setup/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/remote-setup/index.ts)

### 11.5 账号、订阅与周边类命令

#### `/extra-usage`
功能：配置“额度用满以后怎么办”。它的目的不是查看额度，而是设置 overage/extra usage 策略，避免 hit limit 后直接完全停工。  
输入：无参数。  
执行方式：交互模式下是 `local-jsx`，非交互模式下是 `local`。只有账号允许 extra usage 时才启用。  
源码：[src/commands/extra-usage/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/extra-usage/index.ts)

#### `/login`
功能：登录或切换 Anthropic 账号。如果当前是 API key 鉴权，描述会改成“切换账户”；否则更像标准登录入口。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/login/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/login/index.ts)

#### `/logout`
功能：登出当前 Anthropic 账号。  
输入：无参数。  
执行方式：`local-jsx`。  
源码：[src/commands/logout/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/logout/index.ts)

#### `/passes`
功能：分享 Claude Code 试用周或邀请权益；如果你有 referrer reward，还会把“邀请别人后自己获得额外 usage”一起写在文案里。  
输入：无参数。  
执行方式：`local-jsx`。只有资格缓存存在且用户有资格时才显示。  
源码：[src/commands/passes/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/passes/index.ts)

#### `/release-notes`
功能：查看更新说明，是版本发布内容的直接入口。  
输入：无参数。  
执行方式：`local`；支持非交互模式。  
源码：[src/commands/release-notes/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/release-notes/index.ts)

#### `/upgrade`
功能：升级到更高套餐。源码里的文案直接指向 “Upgrade to Max for higher rate limits and more Opus”，所以它本质上是订阅升级入口。  
输入：无参数。  
执行方式：`local-jsx`。只对 `claude-ai` 账户开放。  
源码：[src/commands/upgrade/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/upgrade/index.ts)

#### `/usage`
功能：查看套餐 usage limit，也就是订阅额度面板。和 `/extra-usage` 的区别是：`/usage` 是看额度，`/extra-usage` 是配置超额策略。  
输入：无参数。  
执行方式：`local-jsx`。只对 `claude-ai` 账户开放。  
源码：[src/commands/usage/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/usage/index.ts)

#### `/stickers`
功能：订购 Claude Code 贴纸，是一个典型的周边类命令。  
输入：无参数。  
执行方式：`local`；非交互模式不支持。  
源码：[src/commands/stickers/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/stickers/index.ts)

## 12. 隐藏、条件与内部命令补充说明

前面第 6、7、8 节已经把这些命令做了分类。这里再补一层“功能理解”，帮助你在看 `commands.ts` 时不只知道它们存在，还能大概知道它们为什么存在。

### 12.1 隐藏或调试型公开命令

#### `/heapdump`
功能：把当前进程的 JS heap dump 到桌面，主要用于排查内存泄漏、对象堆积、性能异常等问题。它显然不是给普通用户日常使用的命令，而是开发/调试时的诊断开关。  
执行方式：`local`；默认隐藏。  
源码：[src/commands/heapdump/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/heapdump/index.ts)

#### `/rate-limit-options`
功能：在触发 rate limit 之后弹出后续处理选项，例如是否升级、是否配置额外 usage、是否查看额度。它更像系统流程里的“后续动作页”，不是手动常用命令。  
执行方式：`local-jsx`；默认隐藏，而且只对 Claude.ai 订阅用户开放。  
源码：[src/commands/rate-limit-options/index.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/rate-limit-options/index.ts)

### 12.2 条件 / Feature-Gated 命令

这些命令的共性是：`src/commands.ts` 里已经为它们预留了接入点，但当前本地仓库缺少实现文件，或者只有 feature 打开时才会真正注册。下面的“功能理解”大多基于变量名、路径名和上下文推断，因此我会明确标注“推测”。

#### `/assistant`
功能理解：从 `assistantCommand` 和 `commands/assistant` 命名看，推测它用于 assistant mode 或某种专门的助手式交互入口。  
现状：当前仓库缺实现，无法继续深挖行为细节。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

#### `/buddy`
功能理解：大概率和 companion / buddy 能力相关，可能是更陪伴式、协作式的命令入口。  
现状：当前仓库缺实现。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

#### `/fork`
功能理解：这是独立的 `/fork` 命令位，和 `/branch` 在没有独立 `/fork` 时临时借用 `fork` 作为别名，不是同一个概念。它更像真正的“子代理或子线程分叉命令”。  
现状：只有 `FORK_SUBAGENT` 开启时才可能加入命令表，但当前仓库缺具体实现。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

#### `/peers`
功能理解：从 `UDS_INBOX` gate 和 `commands/peers` 命名看，推测它与 peer session、peer inbox 或多端消息收件箱相关。  
现状：当前仓库缺实现。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

#### `/proactive`
功能理解：大概率用于 proactive / autonomous 模式，让系统更主动地发起行为或建议。  
现状：只有 `PROACTIVE` 或 `KAIROS` 打开时才可能注册；本地仓库缺实现。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

#### `/remote-control-server`
功能理解：从名字看，它更像 remote-control 的服务端调试/守护进程入口，而不是普通用户使用的客户端命令。  
现状：需要 `DAEMON` 和 `BRIDGE_MODE` 双 feature，且当前仓库缺实现。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

#### `/torch`
功能理解：单从命名很难精确判断，推测是实验性项目或内部代号命令。  
现状：只有 `TORCH` feature 打开时才会注册；当前仓库缺实现。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

#### `/workflows`
功能理解：大概率是 workflow scripts 的统一入口，用来列出、管理或执行工作流脚本。  
现状：只有 `WORKFLOW_SCRIPTS` feature 打开时才会注册；当前仓库缺实现。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

### 12.3 有实际实现的内部命令

这一组命令通常只有 Anthropic 内部环境会真正把它们拼进最终命令表，但它们在源码里是有真实实现的，所以很适合拿来理解“内部工作流是怎么嵌进 slash command 体系里的”。

#### `/commit`
功能：读取当前改动并自动生成 git commit。它本质上是“用 prompt 驱动一条标准化提交流”。  
执行方式：`prompt`。  
源码：[src/commands/commit.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/commit.ts)

#### `/commit-push-pr`
功能：在 `/commit` 基础上继续完成 push 和 PR 创建，是更完整的一条提交流水线。  
执行方式：`prompt`。  
源码：[src/commands/commit-push-pr.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/commit-push-pr.ts)

#### `/init-verifiers`
功能：初始化 verifier skill，用来自动验证代码改动。这说明内部工作流里已经把“自动验证器”也做成命令化入口。  
执行方式：`prompt`。  
源码：[src/commands/init-verifiers.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/init-verifiers.ts)

#### `/bridge-kick`
功能：手动注入桥接失败状态，用来测试桥接恢复逻辑是否工作正常。  
执行方式：`local`。  
源码：[src/commands/bridge-kick.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/bridge-kick.ts)

#### `/version`
功能：输出当前 session 真正运行的版本号，用来区分“实际运行版本”和“下载/可升级版本”等概念。  
执行方式：`local`。  
源码：[src/commands/version.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/version.ts)

#### `/ultraplan`
功能：启动更高级的 web 端规划流程。可以把它理解成 `/plan` 的内部增强版本。  
执行方式：`local-jsx`。  
源码：[src/commands/ultraplan.tsx](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands/ultraplan.tsx)

### 12.4 本地版被 stub 掉的内部命令

这批命令在当前仓库里大多只有一个 `isEnabled: () => false` 的占位实现。也就是说，你能从注册表里看到它们“理论上存在”，但本地版不会真的启用它们。

| 命令 | 功能理解 | 当前状态 |
| --- | --- | --- |
| `/ant-trace` | 内部链路/诊断追踪。 | stub，不可用 |
| `/autofix-pr` | 对 PR 做自动修复。 | stub，不可用 |
| `/backfill-sessions` | 会话数据回填或补写。 | stub，不可用 |
| `/break-cache` | 人为打断/清空某类缓存，便于调试缓存问题。 | stub，不可用 |
| `/bughunter` | 深度找 bug 的内部工作流。 | stub，不可用 |
| `/ctx_viz` | 更实验性的上下文可视化工具。 | stub，不可用 |
| `/debug-tool-call` | 调试工具调用细节。 | stub，不可用 |
| `/env` | 查看或导出环境状态。 | stub，不可用 |
| `/good-claude` | 内部实验命令，具体语义无法从公开仓库确认。 | stub，不可用 |
| `/issue` | issue / 问题上报相关流程。 | stub，不可用 |
| `/mock-limits` | 模拟额度/限制命中场景。 | stub，不可用 |
| `/oauth-refresh` | OAuth 刷新调试入口。 | stub，不可用 |
| `/onboarding` | onboarding 流程命令。 | stub，不可用 |
| `/perf-issue` | 性能问题上报或诊断。 | stub，不可用 |
| `/reset-limits` | 重置额度限制状态。 | stub，不可用 |
| `/share` | 分享相关内部入口。 | stub，不可用 |
| `/summary` | 内部摘要/汇总命令。 | stub，不可用 |
| `/teleport` | teleport 流程命令，本地版仅保留占位。 | stub，不可用 |

### 12.5 注册表里引用但当前仓库缺文件的内部命令

#### `/force-snip`
功能理解：从 `HISTORY_SNIP` 命名推测，应该和强制裁剪/截断历史上下文有关。  
现状：注册表有入口，但当前仓库缺文件。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

#### `/subscribe-pr`
功能理解：名字非常直接，大概率是订阅 PR 活动、评论或状态流。  
现状：只有 `KAIROS_GITHUB_WEBHOOKS` feature 打开时才会尝试加载，但当前仓库缺文件。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)

#### `/agents-platform`
功能理解：推测是更平台级的 agents 管理/调试入口，区别于公开版的 `/agents`。  
现状：只在 `USER_TYPE === 'ant'` 的内部环境考虑加载，但当前源码树没有实现文件。  
参考注册点：[src/commands.ts](/home/ad/tianhaoyang/Claude_Code/claude-code-haha/src/commands.ts)
