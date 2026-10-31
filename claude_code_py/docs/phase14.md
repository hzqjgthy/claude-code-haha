# 阶段十四完成项

阶段十四的目标是把 Python 版 Textual UI 从“页面直接拼装”推进到更接近原项目 `FullscreenLayout` 的布局分层。

本阶段已完成：

- `ui/layout/fullscreen.py`
- `ui/layout/modal_manager.py`
- `ui/layout/overlay_manager.py`
- `ui/layout/__init__.py`
- `ui/textual/app.py` 改为通过 `ReplFullscreenLayout` 驱动主布局
- `ui/textual/dialogs.py` 新增内联 pane 版本：
  - `InfoDialogPane`
  - `PermissionDialogPane`

当前结构变化：

- 之前的 Textual app 主要依赖：
  - `Header`
  - `StatusLine`
  - `Horizontal(main-body)`
  - `PromptComposer`
  - `ModalScreen`

- 现在的 Textual app 主要依赖：
  - `Header`
  - `StatusLine`
  - `ReplFullscreenLayout`
  - `Footer`

`ReplFullscreenLayout` 当前已经拆成 4 个布局职责：

1. `scroll-region`
   - transcript
   - tasks panel
2. `overlay-slot`
   - 当前用于权限审批 pane
3. `modal-slot`
   - 当前用于帮助、策略、任务详情、remote 信息 pane
4. `prompt-slot`
   - 底部输入区

这一步与原项目的对应关系：

- 对齐目标：
  - `src/components/FullscreenLayout.tsx`
- 当前实现：
  - 还没有完全做到原项目那种 sticky / pill / transcript divider / scroll subscription 复杂度
  - 但已经完成了最关键的职责拆分：
    - scrollable 区
    - bottom 区
    - overlay 区
    - modal 区

当前行为变化：

- 信息类弹窗不再通过 `push_screen` 走独立 `ModalScreen`
- 权限审批也不再走独立 screen，而是进入 layout 内的 overlay 区
- `Escape` 现在会优先关闭当前 layer：
  - 若有权限审批，执行 `deny_once`
  - 若有信息弹窗，关闭信息 pane

新增测试：

- `tests/unit/test_textual_layout_managers.py`

本阶段验证：

- `python3 -m compileall claude_code_py/src claude_code_py/tests`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/pytest -q`

当前边界：

- 还没有真正实现原项目那种 transcript 滚动跟踪、sticky prompt、new message pill
- 还没有完整 overlay manager / modal manager 与 store 深度联动
- 当前 layout 已经能承接阶段十五的 PromptInput / Messages / StatusLine 深化
