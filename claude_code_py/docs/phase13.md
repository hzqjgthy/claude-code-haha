# 阶段十三完成项

阶段十三的目标是给 Python 版 TUI 建立更接近原项目 `REPL.tsx` 的运行时状态骨架。

本阶段已完成：

- `ui/state/app_state.py`
- `ui/state/store.py`
- `ui/state/selectors.py`
- `ui/runtime/session_runtime.py`
- `ui/runtime/repl_runtime.py`
- `ui/textual/app.py` 改造为消费 runtime/store/selectors
- `ui/textual/controller.py` 增加 UI-only transcript entry 接口

当前结构变化：

- 之前的结构更接近：
  - `Textual app` 直接读取 `controller`
- 现在的结构变成：
  - `controller`
    - 负责会话、命令、工具、权限、任务等核心编排
  - `session_runtime`
    - 负责把 controller 输出同步成统一 UI state
  - `repl_runtime`
    - 负责帮助、策略、任务、remote 弹窗动作和 prompt 提交流程
  - `store`
    - 负责保存当前 UI state
  - `selectors`
    - 负责给 app 提供稳定的读状态接口

这一步的意义：

- 后续阶段十四做 fullscreen layout 时，不需要继续把状态堆到 `app.py`
- 后续阶段十五做 PromptInput / StatusLine / Messages 深化时，也有统一 state 入口
- 当前 TUI 已经从“controller 驱动页面”进入“runtime + store 驱动页面”的阶段

新增测试：

- `tests/unit/test_ui_state.py`
- `tests/unit/test_textual_runtime.py`

本阶段验证：

- `python3 -m compileall claude_code_py/src claude_code_py/tests`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/pytest -q`

当前边界：

- 还没有完整 `AppState selectors + overlay manager + modal manager` 那种原项目级状态复杂度
- 目前 store 主要覆盖 Textual TUI 主循环需要的最核心状态
- 这一步是阶段十四、十五的基础，不是最终 UI 形态
