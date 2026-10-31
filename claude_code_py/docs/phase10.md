# 阶段十完成项

阶段十的目标是给 Python 重构版补上第一版多 Agent 与后台任务能力，并先采用进程内子代理实现。

本阶段已完成：

- `application/task_service.py`
- `tools/agent.py`
- 扩展后的 `domain/tasks.py`
- 进程内子代理执行
- 后台任务注册与状态更新
- REPL 中任务完成/失败通知
- `/tasks` 命令查看任务状态
- `Agent` 工具接入现有 tool/query/repl/print 链路

当前行为说明：

- `Agent` 工具支持：
  - `description`
  - `prompt`
  - `model`
  - `run_in_background`
- 同步子代理会直接返回结果
- 后台子代理会返回 `task_id`
- REPL 中可通过：
  - `/tasks`
  - `/tasks show <task_id>`
  查看后台任务状态
- 后台任务在 REPL 中完成后会以 system message 形式提示
- print/headless 模式下仍可使用同步子代理，但不允许后台任务

这版实现仍然保持边界：

- 先不做 worktree 隔离
- 先不做 remote agent
- 先不做任务持久化
- 先不做 TaskOutput / TaskStop 工具

下一阶段重点会转向完整 TUI、远程与高级能力。
