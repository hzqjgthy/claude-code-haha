# 阶段十二完成项

阶段十二的目标是让 Python 重构版从“能跑”进入“能重复验证、能回归、能打包发布”。

本阶段已完成：

- `tests/parity/*`
- `tests/recovery/*`
- `tests/stress/*`
- `scripts/parity_check.py`
- `scripts/stress_tool_loop.py`
- `scripts/release_check.py`

当前验证层次：

- `unit`
  - 纯业务逻辑、工具、权限、会话、MCP、插件、TUI 控制器
- `integration`
  - CLI 路由、print 模式、Textual CLI 路由
- `parity`
  - 对齐原项目的重要用户契约：
    - REPL 命令链路
    - `/model`
    - `/clear`
    - `/resume ... --fork`
    - 交互式权限审批与会话级记忆
- `recovery`
  - 长 transcript 的 continue / resume / fork 恢复
- `stress`
  - 长工具调用回路压测

新增脚本：

- `python scripts/parity_check.py`
  - 只跑 parity 回归
- `python scripts/stress_tool_loop.py --rounds 25`
  - 跑本地长工具回路压测
- `python scripts/release_check.py`
  - 一键执行：
    - compileall
    - 全量 pytest
    - parity 检查
    - stress 脚本
    - CLI smoke test
    - wheel 打包验证

当前阶段结论：

- Python 版已经具备一组可重复执行的回归验证手段
- 已经具备基础发布前检查流程
- 后续继续对齐原项目时，可以持续复用这一套脚本和测试目录做收口
