# 阶段十一当前进度

阶段十一在原项目里不是一个“简单状态栏 + 输入框”的终端页面，而是一个很重的交互式 Ink/React REPL。

原项目当前的关键入口和 UI 结构是：

- `bin/claude-haha`
  - 默认进入完整 Ink TUI
- `src/entrypoints/cli.tsx`
  - CLI 入口和多种运行模式分发
- `src/screens/REPL.tsx`
  - 主交互屏，负责 transcript、输入、任务、权限、overlay、remote 等大量状态
- `src/components/Messages.tsx`
  - 消息区渲染
- `src/components/PromptInput/*`
  - 输入区、footer、建议、模式切换、快捷键
- `src/components/StatusLine.tsx`
  - 动态状态栏
- `src/components/permissions/*`
  - 真正的权限审批对话框和审批流
- `src/components/TaskListV2.tsx`
  - 任务区与任务详情
- `src/components/RemoteCallout.tsx`
  - remote 相关提示和入口
- `src/components/FullscreenLayout.tsx`
  - 全屏布局、overlay、sticky 区域、modal 容器

所以，Python 版当前这一步还不能说“已经完成了原项目级别的完整 TUI”。更准确的说法是：

- 当前完成了阶段十一的第一部分
- 先补了一个可运行的 Textual UI 壳层
- 方便把现有服务层挂到交互式终端界面上

当前已经完成的部分：

- `ui/textual/controller.py`
- `ui/textual/app.py`
- `ui/textual/state.py`
- `ui/textual/dialogs.py`
- `ui/textual/widgets/*`
- `cli/textual_mode.py`
- `--textual` / `--tui` CLI 入口
- 初版状态栏、任务面板、权限信息弹窗
- remote provider 状态接入
- 交互式权限审批队列
- 会话级权限记忆
- 命令帮助 / 最新任务 / remote 信息弹窗

当前行为说明：

- Textual UI 复用已有服务：
  - `SessionService`
  - `QueryService`
  - `TaskService`
  - `ToolService`
  - MCP / plugins / skills loader
- 顶部状态栏显示：
  - session id
  - 当前模型
  - permission mode
  - remote 状态
  - 当前运行状态
- 消息区、状态栏、任务区、输入区已经拆成独立 widget
- 右侧任务面板直接消费 `TaskService`
- `F1` 打开命令帮助
- `F2` 打开权限策略信息
- 遇到 `ask` 权限时会自动弹出审批对话框
- 审批支持：
  - Approve Once
  - Approve Session
  - Deny Once
  - Deny Session
- `Approve Session` / `Deny Session` 会在本会话内记住规则
- `F5` 手动刷新状态
- `q` 或 `Ctrl+C` 退出
- `--textual "prompt"` 会在启动后直接提交首条 prompt

当前与原项目的主要偏差：

- 还没有对齐 `src/screens/REPL.tsx` 那种集中式 AppState 驱动结构
- 还没有对齐 `FullscreenLayout` 的 scrollable / bottom / modal / overlay 分层
- 还没有对齐 `PromptInput` 的完整建议系统、模式切换和复杂快捷键
- 还没有对齐原项目的多种权限审批子组件族，只实现了统一审批弹窗
- 还没有对齐 `TaskListV2` 的完整任务导航和各类详情面板
- 还没有对齐 remote callout / bridge / direct connect / ssh 等 UI 流程
- 还没有对齐 fullscreen transcript、消息动作、选择器、sticky prompt 等复杂行为

后续对齐时，应该按原项目模块继续拆：

1. 先补 Python 版 `AppState` / `UiState`，不要把所有交互都塞在 `TextualSessionController`
2. 再补 `FullscreenLayout` 对应的 Textual 布局层
3. 再补消息区、输入区、footer、任务区的独立组件
4. 再补真正的权限审批弹窗和任务详情弹窗
5. 最后再接 remote / bridge 相关 UI

结论：

- 当前只完成了“阶段十一初版 TUI 壳层”，还没有达到“按原项目 REPL 完整重构”的程度
- 后续阶段十一应继续细化，而不是直接宣布 UI 已经完全完成
