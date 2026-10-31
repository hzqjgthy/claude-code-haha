# 阶段十五完成项

阶段十五的目标是把 Python 版最核心的交互层继续往原项目靠拢，重点深化：

- PromptInput
- StatusLine
- Messages

本阶段已完成：

- `ui/state/app_state.py`
  - 新增：
    - `PromptState`
    - `PromptSuggestionState`
    - `StatusDetailState`
- `ui/runtime/session_runtime.py`
  - 新增 `build_prompt_state()`
- `ui/runtime/repl_runtime.py`
  - 新增 `update_prompt_text()`
  - refresh 会保留并重建 prompt state
- `ui/textual/controller.py`
  - 新增：
    - `status_detail_snapshot()`
    - `command_suggestions()`
- `ui/textual/messages/renderers.py`
  - 新增 transcript 分类渲染
- `ui/textual/widgets/prompt_composer.py`
  - 新增 mode、hint、suggestions 渲染
- `ui/textual/widgets/status_line.py`
  - 支持更丰富的状态字段
- `ui/textual/widgets/transcript.py`
  - 改为使用专门的消息渲染器
- `ui/textual/app.py`
  - 新增 `on_input_changed`
  - 输入时持续刷新 prompt state

本阶段的用户可见变化：

## PromptInput

- 输入区现在会显示当前模式：
  - `PROMPT`
  - `COMMAND`
- 输入 `/` 开头内容时，会进入 command mode
- command mode 会给出 slash command 建议
- 空输入时会显示基础提示和常用命令建议

## StatusLine

- 状态栏不再只显示 session/model/permission
- 现在还会显示：
  - session title
  - project
  - cwd
  - transcript entries
  - user entries
  - assistant entries
  - task count
  - command count
  - remote 状态
  - 当前 runtime state

## Messages

- transcript 渲染不再是单一 label
- 现在会对下面这些内容做更细分类：
  - `Tool call:`
  - `Tool result:`
  - `Permission requested:`
  - `warning:`
- 普通 user / assistant message 的 label 也更接近真实对话语义：
  - `you`
  - `claude`

新增测试：

- `tests/unit/test_textual_prompt_state.py`

本阶段验证：

- `python3 -m compileall claude_code_py/src claude_code_py/tests`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/pytest -q`

当前边界：

- PromptInput 还没有历史搜索、复杂快捷键、真正的 footer suggestion 体系
- Messages 还没有原项目那种 message actions、selection、rewind、search
- StatusLine 还没有上下文窗口、token/cost/rate-limit 等高级字段

但这一步已经把三条主线从“能用”推进到了“开始像原项目的交互模型”。
