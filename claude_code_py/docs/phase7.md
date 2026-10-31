# 阶段七完成项

阶段七的目标是恢复用户主动调度系统的能力，并给 Python 重构版接上第一版 Commands 与 Skills。

本阶段已完成：

- `commands/loader.py`
- 基础 slash command 解析与注册表
- 内置命令：
  - `/help`
  - `/resume`
  - `/clear`
  - `/model`
  - `/review`
  - `/skills`
- `skills/parser.py`
- `skills/loader.py`
- markdown skill frontmatter 解析
- REPL 中接入 slash commands
- REPL 中接入 user-invocable skills

当前行为说明：

- 以 `/` 开头的输入会被当成 slash command
- `/review` 会生成一条面向代码审查的 prompt
- `/model` 会修改当前 REPL 会话后续调用使用的 model
- `/clear` 会创建新的空会话
- `/resume` 会在 REPL 内恢复已有会话，或列出最近会话
- `/skills` 会列出已加载 skills，并支持 `reload`
- skills 目录当前支持：
  - `~/.claude/skills`
  - `<workspace>/.claude/skills`
- 支持 `SKILL.md` 与普通 `.md` 技能文件
- `user-invocable: true` 的 skill 会暴露为 slash command

这版实现仍然保持边界：

- 先不做插件提供 commands
- 先不做复杂 command 权限编排
- 先不做 model-only skills 调度
- 先不做完整 command picker UI

下一阶段重点会转向 MCP 支持。
