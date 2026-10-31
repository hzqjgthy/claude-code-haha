# 面向 1:1 完整平移的后续开发规划

## 1. 文档目标

这份文档的目标很明确：

**把 `claude_code_py/` 从“核心骨架可运行”继续推进到“原项目完整产品能力的 1:1 Python 平移版”。**

这里的关键词不是“能用”，而是：

- 功能对齐
- 交互对齐
- 运行模式对齐
- 工具面与命令面对齐
- 远程与桥接能力对齐
- 行为契约对齐

也就是说，接下来的开发目标不再是继续做一个“Python 风格的类似产品”，而是：

**严格参考原项目，尽量按原项目模块边界、行为契约和用户体验去做 Python 平移。**

---

## 2. 总体目标定义

为了避免后续开发过程中目标漂移，先定义什么叫“1:1 完整平移版”。

达到目标时，Python 版应满足：

### 2.1 用户视角

- 主要 CLI 命令可用
- 主要交互式 REPL/TUI 行为可用
- 主要工具集可用
- 主要权限审批流可用
- 会话恢复、compact、memory、history 等长期使用能力可用
- MCP、插件、skills、agent、remote、bridge 等主线产品能力可用

### 2.2 架构视角

- Python 版有与原项目大体对应的模块分层
- 不是把所有功能堆到少量大文件里
- 能建立“原模块 -> Python 模块”的稳定映射

### 2.3 测试视角

- 有一套可重复执行的双实现对齐测试
- 核心场景能同时验证原项目和 Python 版
- 对“行为偏差”有明确记录，而不是靠人工印象判断

### 2.4 发布视角

- Python 版可独立安装、运行、测试、打包
- 将 `claude_code_py/` 整体移出当前仓库后仍能运行
- 有明确的发布前检查流程

---

## 3. 接下来开发的基本原则

如果目标是 1:1 平移，后面必须坚持下面这些原则。

### 3.1 参考原项目，优先复刻行为

优先顺序应该是：

1. 原项目当前行为是什么
2. Python 版如何尽量复刻
3. 只有在 Python 技术限制下，才考虑适度调整实现细节

不能反过来：

1. 先按 Python 习惯设计一套新行为
2. 再说“差不多”

### 3.2 优先建立模块映射，不要无边界生长

后续每补一个功能，最好都能回答：

- 它在原项目哪个文件或哪组文件里
- Python 版应该落在哪个模块

建议持续维护一张映射表：

- 原项目入口
- 原项目组件
- 原项目 commands
- 原项目 tools
- 原项目 permissions
- 原项目 bridge / remote

### 3.3 先补核心产品主线，再补外围能力

如果要做 1:1，对齐顺序不能乱。

优先级应当是：

1. REPL/TUI 交互主线
2. commands + tools 主线
3. permissions + sandbox 主线
4. session/memory/compact 主线
5. MCP/plugins/agents/remote 主线
6. auth/analytics/IDE/LSP/desktop/mobile 等外围能力

### 3.4 每个阶段都要附带对齐测试

后续不能只做功能，不做验证。

每补一个大块能力，都应该同步补：

- parity fixtures
- recovery cases
- stress cases
- release check entry

---

## 4. 接下来建议的总体路线

建议把后续开发拆成 10 个阶段，从阶段 13 开始继续推进。

| 阶段 | 主题 | 目标 |
|---|---|---|
| 13 | Runtime 与 AppState 对齐 | 建立 Python 版 REPL 运行时状态骨架 |
| 14 | Fullscreen TUI 对齐 | 对齐 REPL 主布局、overlay、modal、bottom 区域 |
| 15 | PromptInput / StatusLine / Messages 对齐 | 对齐最核心交互体验 |
| 16 | Commands 全面扩展 | 把常用命令面补齐到可对标原项目 |
| 17 | Tools 全面扩展 | 把核心工具面补齐到可对标原项目 |
| 18 | Permission / Sandbox 深度对齐 | 对齐审批流、安全规则、sandbox 交互 |
| 19 | Session / Compact / Memory / History | 对齐长期会话能力 |
| 20 | MCP / Plugins / Agent / Tasks 深化 | 对齐扩展能力与任务体系 |
| 21 | Remote / Bridge / Direct Connect / SSH | 对齐远程能力 |
| 22 | Auth / Policy / Ecosystem / 最终对拍发布 | 收口所有产品外围能力并做最终验证 |

---

## 5. 阶段 13：Runtime 与 AppState 对齐

### 目标

把 Python 版当前“控制器驱动的初版 TUI”提升为更接近原项目 `REPL.tsx` 的状态组织方式。

### 为什么要先做这个

当前 Python 版已经有：

- `TextualSessionController`
- widget / dialogs / state 初版拆分

但还没有一个足够接近原项目的 UI 运行时状态层。  
如果不先补这层，后面继续补输入系统、消息动作、overlay、remote、tasks 时会越来越乱。

### 重点参考原项目

- `src/screens/REPL.tsx`
- `src/state/*`
- `src/bootstrap/state.ts`
- `src/components/App.tsx`

### Python 侧建议新增

- `ui/state/app_state.py`
- `ui/state/store.py`
- `ui/state/selectors.py`
- `ui/runtime/session_runtime.py`
- `ui/runtime/repl_runtime.py`

### 本阶段要做的事

- 把当前散落在 controller/app 里的 UI 状态拆成统一 store
- 明确区分：
  - domain state
  - session state
  - ui state
  - transient overlay state
- 为后续功能预留：
  - focused dialog
  - spinner state
  - transcript search state
  - selected message state
  - task detail state
  - remote state

### 验收标准

- 后续 UI 增强不再需要把所有状态堆到 `controller.py`
- 能建立接近原项目的 “store + selectors + runtime” 组织方式

---

## 6. 阶段 14：Fullscreen TUI 对齐

### 目标

把当前 Textual TUI 从“几个 panel 拼起来的页面”升级为接近原项目 `FullscreenLayout` 的布局容器。

### 重点参考原项目

- `src/components/FullscreenLayout.tsx`
- `src/screens/REPL.tsx`
- `src/components/TaskListV2.tsx`
- `src/components/TeammateViewHeader.tsx`

### 本阶段要做的事

- 建立统一的 fullscreen layout
- 明确 4 个区域：
  - scrollable transcript
  - bottom prompt/input area
  - overlay layer
  - modal layer
- 让 task 区、permission 区、prompt 区的定位关系更接近原项目
- 支持：
  - sticky bottom
  - scroll state
  - unseen/new message divider
  - focused dialog routing

### Python 侧建议新增

- `ui/layout/fullscreen.py`
- `ui/layout/overlay_manager.py`
- `ui/layout/modal_manager.py`

### 验收标准

- UI 布局模型不再是简单 `status + horizontal + input`
- 后续弹窗、权限、任务详情、message actions 能稳定接入

---

## 7. 阶段 15：PromptInput / StatusLine / Messages 对齐

### 目标

把最核心的交互层做深，这一阶段是“像不像原项目”的关键。

### 重点参考原项目

- `src/components/PromptInput/*`
- `src/components/StatusLine.tsx`
- `src/components/Messages.tsx`
- `src/components/messages/*`
- `src/components/MessageSelector.tsx`

### 本阶段要做的事

#### PromptInput

- 增加输入模式
- 增加 footer suggestions
- 增加 slash command suggestions
- 增加 history search
- 增加 queued commands
- 增加更完整的快捷键绑定
- 增加输入状态提示

#### StatusLine

- 对齐更多状态字段：
  - model
  - permission mode
  - cwd / project
  - session
  - context window usage
  - task / remote 状态
- 为后续接入 hook / command status 留口

#### Messages

- 按消息类型拆分 renderer
- 支持 tool_use / tool_result 的更细渲染
- 支持 system / warning / status 类型消息
- 支持基础 message selection / action

### Python 侧建议新增

- `ui/textual/messages/*`
- `ui/textual/prompt/*`
- `ui/textual/status/*`

### 验收标准

- Python 版最核心的交互体验明显向原项目靠拢
- 用户不再只是在“一个简化输入框”里使用系统

---

## 8. 阶段 16：Commands 全面扩展

### 目标

把当前极薄的命令面扩展成真正可对标原项目的命令体系。

### 当前已有

- `/help`
- `/resume`
- `/clear`
- `/model`
- `/review`
- `/skills`
- `/tasks`

### 优先补齐的命令

优先级最高的一批：

- `/config`
- `/diff`
- `/permissions`
- `/status`
- `/theme`
- `/cost`
- `/memory`
- `/compact`
- `/files`
- `/hooks`
- `/plugin`
- `/mcp`
- `/doctor`
- `/export`
- `/rewind`
- `/rename`

第二批：

- `/agents`
- `/plan`
- `/context`
- `/output-style`
- `/sandbox-toggle`
- `/remote-env`
- `/session`
- `/tag`

第三批：

- `/ide`
- `/login`
- `/logout`
- `/voice`
- `/mobile`
- `/desktop`

### 重点参考原项目

- `src/commands/*`
- `src/commands.ts`

### 验收标准

- 常用 slash command 已基本覆盖
- 命令行为尽量与原项目一致
- 命令不只是“显示信息”，而是能真正驱动 REPL 状态变化

---

## 9. 阶段 17：Tools 全面扩展

### 目标

把工具面从“少数核心工具”扩展到原项目常用工具集。

### 当前已有

- Bash
- Read
- Edit
- Write
- WebFetch
- Agent
- MCP wrapper

### 优先补齐的工具

第一批：

- `Glob`
- `Grep`
- `TodoWrite`
- `WebSearch`
- `PowerShell`
- `NotebookEdit`
- `Sleep`
- `SkillTool`

第二批：

- `TaskCreate`
- `TaskGet`
- `TaskList`
- `TaskOutput`
- `TaskStop`
- `TaskUpdate`
- `TeamCreate`
- `TeamDelete`
- `SendMessage`

第三批：

- `ListMcpResources`
- `ReadMcpResource`
- `McpAuth`
- `ToolSearch`
- `Workflow`
- `Config`
- `AskUserQuestion`

### 暂后考虑

- `Tungsten`
- `ComputerUse`
- 高度平台绑定的工具

### 重点参考原项目

- `src/tools/*`
- `src/Tool.ts`

### 验收标准

- 常见工作流不再频繁因为“缺工具”中断
- 工具 schema、summary、permission target 更接近原项目

---

## 10. 阶段 18：Permission / Sandbox 深度对齐

### 目标

把当前基础权限系统提升到原项目级别的安全交互系统。

### 当前已有

- allow / deny / ask
- session 级记忆
- Textual 审批弹窗

### 还必须补的内容

- 按工具类型拆分专用审批弹窗
- Bash / WebFetch / FileEdit / FileWrite / NotebookEdit / PowerShell 的专用审批视图
- persist / always allow / always deny 逻辑
- sandbox network permission 交互
- auto mode / bypass permissions / plan mode 切换逻辑
- 更细粒度 command / path / domain 匹配
- denial tracking
- rule shadowing 检测
- 和 hooks / agent / remote 的审批协同

### 重点参考原项目

- `src/components/permissions/*`
- `src/utils/permissions/*`
- `src/utils/sandbox/sandbox-adapter.ts`

### 验收标准

- 权限系统不再只是“规则 + 一个弹窗”
- 真正具备原项目的安全交互深度

---

## 11. 阶段 19：Session / Compact / Memory / History

### 目标

补齐长期会话使用能力。

### 当前已有

- transcript
- session index
- continue / resume / fork

### 还必须补的内容

- compact
- micro compact
- post compact cleanup
- session memory
- memory extract
- file history snapshot / rewind
- export / share
- rename session
- session backgrounding
- concurrent sessions

### 重点参考原项目

- `src/services/compact/*`
- `src/services/SessionMemory/*`
- `src/utils/sessionStorage.ts`
- `src/utils/fileHistory.ts`
- `src/utils/sessionRestore.ts`

### 验收标准

- 长会话不只是能恢复，还能持续工作
- 用户能够在长期项目里稳定使用 Python 版

---

## 12. 阶段 20：MCP / Plugins / Agent / Tasks 深化

### 目标

把扩展能力从“基础版”提升到原项目主线级别。

### MCP

需要补：

- resources
- auth
- reconnect
- registry
- elicitation
- 完整状态管理 UI

### Plugins

需要补：

- marketplace
- trust warning
- install / update / validate
- manage UI

### Agent / Tasks

需要补：

- 更完整的 task model
- task detail dialogs
- teammate / team / swarm
- task output / stop / update tool 对齐
- 多类型 task

### 重点参考原项目

- `src/services/mcp/*`
- `src/components/mcp/*`
- `src/commands/plugin/*`
- `src/services/plugins/*`
- `src/tasks/*`
- `src/components/tasks/*`
- `src/tools/AgentTool/*`

### 验收标准

- MCP 不再只是“tool 接入”
- 插件不再只是“本地目录加载”
- Agent / task 不再只是“简化子代理”

---

## 13. 阶段 21：Remote / Bridge / Direct Connect / SSH

### 目标

把当前最大缺口之一补起来。

### 当前已有

- `RemoteProvider`
- `LocalRemoteProvider`
- TUI 显示 remote status

### 还必须补的内容

- Remote session manager
- session websocket
- bridge session lifecycle
- remote control
- direct connect
- SSH session
- reconnect / heartbeat / archive
- remote permission bridge
- remote transcript hydration

### 重点参考原项目

- `src/bridge/*`
- `src/remote/*`
- `src/cli/remoteIO.ts`
- `src/hooks/useRemoteSession.ts`
- `src/hooks/useDirectConnect.ts`
- `src/hooks/useSSHSession.ts`

### 风险提示

这是后续阶段里风险最高的一块。  
建议在前面阶段把 UI、权限、session、task 基础都做稳之后再进入。

### 验收标准

- Python 版不再只支持本地单机会话
- remote / bridge 能真正成为产品级能力

---

## 14. 阶段 22：Auth / Policy / Ecosystem / 最终对拍发布

### 目标

补齐剩余的产品外围能力，并做最终 1:1 收口。

### 需要补的能力

- login / logout / OAuth
- policy limits
- remote managed settings
- analytics / feature gates
- updater / release notes
- billing / rate-limit / passes
- IDE / LSP
- desktop / mobile / voice
- Claude in Chrome / computer-use 等外围能力

### 最终对拍需要新增的东西

- `docs/parity_matrix.md`
- `tests/golden/*`
- `tests/dual_run/*`
- `scripts/dual_run_compare.py`

### 双实现对拍建议

目标不是只测 Python 版自己，而是：

- 用同一套输入场景
- 同时跑原项目和 Python 版
- 比较：
  - 命令行为
  - tool 调用序列
  - session 恢复行为
  - 权限审批行为
  - 关键输出结构

### 验收标准

- Python 版已不是“功能相似”
- 而是“关键行为可系统性对拍”

---

## 15. 并行工作流建议

如果后续要长期推进，建议把工作拆成 6 条并行工作流。

### 工作流 A：Runtime / UI

- AppState
- FullscreenLayout
- PromptInput
- Messages
- StatusLine
- dialogs / overlay

### 工作流 B：Commands / Tools

- commands 扩展
- tools 扩展
- tool summary / schema / rendering

### 工作流 C：Security / Session

- permissions
- sandbox
- compact
- memory
- history

### 工作流 D：Extensibility

- MCP
- plugins
- skills
- agents
- tasks

### 工作流 E：Remote

- bridge
- remote
- direct connect
- SSH

### 工作流 F：Verification / Release

- parity
- recovery
- stress
- dual-run compare
- packaging

---

## 16. 每个阶段都必须交付的产物

为了避免后续阶段又回到“做了很多但难以确认是否对齐”的状态，建议每一阶段都固定交付下面这些内容。

### 代码产物

- 对应功能模块代码
- 对应测试
- 对应文档

### 对齐产物

- 原项目参考文件列表
- Python 对应模块列表
- 当前仍未覆盖的差异点

### 验证产物

- 新增 parity case
- recovery case
- stress case
- release_check 补充项

---

## 17. 建议维护的长期文档

除了这份规划文档，建议你后续再长期维护下面几份文档。

### 17.1 `docs/parity_matrix.md`

记录：

- 命令对齐情况
- 工具对齐情况
- UI 交互对齐情况
- 远程能力对齐情况

### 17.2 `docs/module_mapping.md`

记录：

- 原项目模块
- Python 对应模块
- 当前状态

### 17.3 `docs/open_gaps.md`

记录：

- 当前阶段仍未解决的问题
- 风险项
- 阻塞项

---

## 18. 最终建议

如果你的目标已经明确成：

**“原项目完整产品能力的 1:1 Python 平移版”**

那后续开发一定要接受两件事：

### 第一件事

这不再是普通重构，而是一个**长期的大型平移工程**。

原因很简单：

- 原项目体量巨大
- 产品能力非常多
- 复杂度主要不在单点技术，而在交互、状态、扩展、远程、权限、安全、平台能力的叠加

### 第二件事

真正的关键不只是“继续写功能”，而是：

- 保持模块边界清晰
- 保持对原项目的持续映射
- 保持阶段性交付
- 保持双实现对拍能力

只有这样，最后做出来的才会是：

- 可学习
- 可维护
- 可继续推进
- 真正接近原项目完整能力

而不是一个越来越大的“Python 版另一个产品”。

