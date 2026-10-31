# 阶段四完成项

阶段四的目标是把“工具能不能执行”从各个工具实现里抽离出来，形成独立、可测试、可组合的权限系统。

本阶段已完成：

- `PermissionRule / PermissionContext / PermissionDecision` 领域模型
- `permissions/rules.py`
- `permissions/decision.py`
- `permissions/engine.py`
- `application/permission_service.py`
- `ToolService` 统一权限前置检查
- headless `--print` 模式权限接入
- CLI 权限参数：
  - `--permission-mode`
  - `--allow-tool`
  - `--deny-tool`
  - `--ask-tool`
- 与原项目更接近的兼容输入：
  - `acceptEdits` / `bypassPermissions`
  - `--allowed-tools` / `--disallowed-tools`

当前行为说明：

- 规则来源支持：
  - `user_settings`
  - `project_settings`
  - `session`
  - `cli_arg`
- 决策行为支持：
  - `allow`
  - `deny`
  - `ask`
- headless 模式下没有交互式审批 UI，因此 `ask` 会按“拒绝并给出原因”处理
- `accept_edits` 模式默认允许 `Read / Write / Edit`
- `plan` 模式默认只允许 `Read`
- `bypass_permissions` 模式直接放行

这版实现仍然保持第一版边界：

- 先不实现原项目里的复杂 classifier
- 先不实现危险命令自动分析
- 先把规则来源、优先级和执行入口抽清楚

下一阶段重点会转向更完整的会话能力与 resume。
