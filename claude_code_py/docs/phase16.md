# 阶段十六完成项（第一批）

阶段十六的目标是把 Python 版当前偏薄的 slash command 面继续往原项目靠拢。

这一轮没有去做“只有名字没有能力”的空命令，而是优先补齐了一批能够直接复用现有运行时、并且在 REPL / Textual 两条链路里马上生效的命令。

本阶段新增：

- `commands/builtins/config.py`
- `commands/builtins/doctor.py`
- `commands/builtins/files.py`
- `commands/builtins/mcp.py`
- `commands/builtins/permissions.py`
- `commands/builtins/plugin.py`
- `commands/builtins/rename.py`
- `commands/builtins/status.py`

同时补强：

- `commands/loader.py`
  - `CommandContext` 现在额外持有：
    - container
    - permission_service
    - tool_context
    - MCP configs / tool definitions / manager
    - remote_provider
- `application/permission_service.py`
  - 新增：
    - `list_rules()`
    - `clear_rules()`
    - `current_mode()`
    - `set_mode()`
- `application/session_service.py`
  - 新增 `rename_session()`
- `tools/file_context.py`
  - 新增文件上下文跟踪工具
- `tools/file_read.py`
- `tools/file_edit.py`
- `tools/file_write.py`
  - 现在会把访问过的文件加入当前 tool context
- `ui/textual/controller.py`
  - status / permission summary 现在读取运行时真实状态
  - bare `/` 的 command suggestions 改为常用命令优先

本阶段新增的用户可见命令：

## `/status`

- 显示当前 session id、title、parent session
- 显示 model、permission mode、workspace、cwd
- 显示 message / task / file context / plugin / MCP 统计

## `/doctor`

- 显示 app/path/storage 配置
- 显示 transcript / session index 路径
- 显示模型与认证配置状态
- 显示 plugin / skill / MCP / remote 基础健康信息

## `/config`

- 显示当前运行配置快照
- 包括 app、paths、current model、default model、system prompt、plugin / MCP 配置数

## `/permissions`

- `/permissions`
  - 查看当前 permission mode 与全部规则
- `/permissions mode <mode>`
  - 动态切换运行时 permission mode
- `/permissions allow <rule>`
- `/permissions deny <rule>`
- `/permissions ask <rule>`
  - 追加 session 级规则
- `/permissions clear-session`
  - 清理 session 级规则

这一步很重要，因为它已经不只是“看状态”，而是开始真正驱动运行时权限行为。

## `/plugin`

- `/plugin`
  - 列出已加载插件
- `/plugin show <name>`
  - 查看单个插件详情
- `/plugin reload`
  - 重新加载 plugin + skill + plugin command
- `/plugin errors`
  - 查看插件加载错误

## `/mcp`

- `/mcp`
  - 列出已加载的 MCP server
- `/mcp tools`
  - 查看所有已注册 MCP tools
- `/mcp show <server_name>`
  - 查看单个 server 的 transport / source / tools 详情

## `/files`

- `/files`
  - 列出当前 tool context 内的文件
- `/files clear`
  - 清理当前文件上下文

当前定义里，`Read / Edit / Write` 会自动把访问文件记进这个列表。  
这不是原项目完整的 file state cache，但已经比“完全没有 /files”更接近原项目能力。

## `/rename`

- `/rename`
  - 查看当前 session title
- `/rename <new title>`
  - 修改当前 session 的标题，并更新 session index

新增测试：

- `tests/unit/test_commands.py`

补充测试覆盖：

- `tests/unit/test_file_tools.py`

本阶段验证：

- `python3 -m compileall src tests`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/pytest -q`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/python scripts/release_check.py`

当前边界：

- 这一轮只完成了阶段十六的第一批高价值命令
- 仍未完成的重点命令包括：
  - `/diff`
  - `/compact`
  - `/memory`
  - `/hooks`
  - `/export`
  - `/rewind`
  - `/context`
  - `/plan`
  - `/session`
- `/mcp` 和 `/plugin` 当前还是“信息 + reload + inspect”导向，还没有原项目那种完整设置面板与启停流
- `/files` 当前基于 Python 版的 file context 跟踪，不是原项目完整的 readFileState/cache 体系

所以这一步可以定义为：

**第十六阶段已经真正开始落地，并补上了第一批能驱动状态的核心命令，但距离原项目完整 command 面仍有明显差距。**

---

## 第二批补充

在第一批基础上，这一轮继续补了四个命令：

- `commands/builtins/context.py`
- `commands/builtins/export.py`
- `commands/builtins/plan.py`
- `commands/builtins/session.py`

新增行为：

### `/plan`

- 更贴近原项目 `plan` 命令的主线行为
- 当当前不在 `plan` mode 时：
  - `/plan`
    - 直接切换到 `plan` mode
  - `/plan <request>`
    - 先切换到 `plan` mode
    - 再把 `<request>` 继续送进 query loop
- 当已经在 `plan` mode 时：
  - `/plan`
    - 展示当前 `plan.md`
  - `/plan open`
    - 当前只返回 plan 文件路径说明
    - 外部编辑器联动尚未实现

当前的 plan 文件路径约定为：

- `<workspace>/.claude_code_py/plan.md`

### `/export`

- 支持导出当前 conversation 为文本文件
- `/export notes/demo`
  - 会输出到 `<cwd>/notes/demo.txt`
- `/export`
  - 会按时间戳 + 首条用户消息自动生成默认文件名

### `/context`

- 支持查看当前会话上下文快照
- 当前展示的是：
  - 原始 session history
  - message count / user / assistant / tool 统计
  - first / last message preview
  - 最近若干条消息预览

这里我保持了准确表述：

- 当前 Python 版还没有实现原项目那套 compact/context-collapse 后的真正 API view
- 所以 `/context` 现在展示的是 “raw conversation snapshot”

### `/session`

- 原项目的 `/session` 更偏 remote session 视图
- 当前 Python 版 remote/bridge 体系还没完成
- 所以当前实现会：
  - 若无 remote session
    - 明确提示 `Not in remote mode.`
    - 同时给出当前 local session 信息
  - 若未来 remote provider 变为 connected
    - 可以直接复用当前命令输出 remote session url / detail

新增测试：

- `tests/unit/test_commands.py`
  - 新增 `/plan`
  - 新增 `/export`
  - 新增 `/context`
  - 新增 `/session`

本轮验证：

- `python3 -m compileall claude_code_py/src/claude_code_py/commands claude_code_py/tests/unit/test_commands.py`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/pytest -q`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/python scripts/release_check.py`

这一轮完成后，第十六阶段未完成的重点命令仍然包括：

- `/diff`
- `/compact`
- `/memory`
- `/hooks`
- `/rewind`
- `/session`
  - 远程完整能力仍未对齐
- `/export`
  - 目前只有文本导出
- `/context`
  - 目前还是 raw snapshot，不是完整 API view

所以当前状态可以更准确地描述为：

**第十六阶段已经完成两批高价值命令补齐，command 面明显更接近原项目，但仍未达到原项目完整命令系统的 1:1 对齐。**

---

## 第三批补充

这一轮继续补了四个命令：

- `commands/builtins/diff.py`
- `commands/builtins/hooks.py`
- `commands/builtins/memory.py`
- `commands/builtins/rewind.py`

同时补强：

- `providers/storage/transcript_store.py`
  - 新增 `overwrite_messages()`
- `application/session_service.py`
  - 新增 `rewrite_messages()`
- `ui/textual/controller.py`
  - 新增 transcript reset
  - `clear / resume / rewind` 这类会改 session state 的命令现在能刷新 Textual transcript

### `/rewind`

这是这一轮最重要的命令，因为它已经不只是“展示入口”，而是开始具备真实行为。

当前支持：

- `/rewind`
  - 列出当前会话所有 user turn 的 rewind 点
- `/rewind last`
  - 回退掉最新一轮 user turn 及其后续消息
- `/rewind <turn_number>`
  - 回退到指定 user turn 之前

并且：

- 会真实改写 session transcript 文件
- 会更新 session index
- 在 Textual 模式下，消息区会同步刷新
- 在 Textual 模式下，`/rewind` 基础入口现在会打开 selector dialog
- selector 中每个 rewind 点都会附带 turn preview，并可直接提交对应 `/rewind <turn_number>`

这一步虽然还没有原项目那种更深的 message-selector / restore-files 一整套工作流，但已经进入真实可用的交互式回退体验。

### `/diff`

当前实现聚焦原项目同类命令最核心的用途：

- 查看当前 git working tree 差异
- `/diff`
  - 展示 `git status --short`
  - 展示 staged / unstaged diff stat
- `/diff full`
  - 展示完整 patch

### `/memory`

当前先按原项目常见 memory 路径约定做 inspection / init：

- `~/.claude/CLAUDE.md`
- `<workspace>/CLAUDE.md`
- `<workspace>/.claude/CLAUDE.md`
- `<workspace>/CLAUDE.local.md`
- `<workspace>/.claude/rules/*.md`

当前支持：

- `/memory`
  - 列出这些 memory 文件及存在状态
  - 在 Textual 中打开 memory selector
- `/memory path <target>`
  - 查看某个 memory 文件路径
- `/memory init <target>`
  - 初始化某个 memory 文件
- `/memory show <target>`
  - 查看某个 memory 文件内容
- `/memory edit <target>`
  - 在 Textual 中打开 inline editor，并直接保存回文件

这里我刻意没有把它描述成“完整 memory 系统”：

- 原项目里 `/memory` 更接近完整的交互式编辑入口
- 当前 Python 版虽然已经有 selector + inline editor，但还没有 auto-memory、team memory、session memory 那整套体系

### `/hooks`

当前支持：

- 检查 `~/.claude/settings.json`
- 检查 `<workspace>/.claude/settings.json`
- 列出其中的 `hooks` 配置概览
- 列出插件 manifest 里声明的 hooks

但要明确：

- 当前只是 hook config inspection
- Python 版还没有实现原项目复杂的 hook execution / watcher / post-tool-use / stop hooks 体系

新增测试：

- `tests/unit/test_commands.py`
  - 新增 `/rewind`
  - 新增 `/diff`
  - 新增 `/memory`
  - 新增 `/hooks`

本轮验证：

- `python3 -m compileall claude_code_py/src/claude_code_py/commands claude_code_py/src/claude_code_py/application claude_code_py/src/claude_code_py/providers/storage claude_code_py/src/claude_code_py/ui/textual/controller.py claude_code_py/tests/unit/test_commands.py`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/pytest -q`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/python scripts/release_check.py`

当前第十六阶段剩余的重点命令缺口，仍然包括：

- `/compact`
- `/memory`
  - 仍缺 editor integration / session memory / team memory
- `/hooks`
  - 仍缺完整 hooks runtime
- `/diff`
  - 仍缺原项目 dialog 级交互体验
- `/rewind`
  - 仍缺 message selector UI

所以这一步之后，更准确的表述是：

**第十六阶段的 command 面已经补到第三批，核心常用命令覆盖度明显提高，但和原项目完整产品级命令体验相比，仍然主要差在 interactive UI 和高级 runtime。**

---

## 交互式增强

这一轮不再只是继续增加命令，而是把一批已有命令往更接近原项目的交互式产品体验推进。

本轮补强：

- `commands/loader.py`
  - `CommandResult` 现在支持附带 dialog / selector / editor metadata
- `ui/textual/controller.py`
  - 新增 command-triggered info dialog / selector dialog / editor dialog request
- `ui/runtime/repl_runtime.py`
  - slash command 执行后会把 command dialog 注入当前 Textual state
  - 新增 modal precedence：`editor > selector > info`
- `ui/textual/dialogs.py`
  - `InfoDialogPane` 改为可滚动展示
  - 新增 `SelectorDialogPane`
- `ui/textual/widgets/prompt_overlay.py`
  - 新增独立 prompt overlay，显示 suggestions 与 notices
- `ui/textual/widgets/transcript.py`
  - 新增 sticky prompt
  - 新增 new messages pill
  - 新增 transcript search / jump

### 当前 Textual 已支持命令面板的命令

- `/status`
- `/config`
- `/doctor`
- `/context`
- `/diff`
- `/files`
- `/hooks`
- `/memory`
- `/mcp`
- `/permissions`
- `/plan`
- `/plugin`
- `/session`
- `/tasks`

### 当前已支持 selector dialog 的命令

- `/memory`
  - 基础入口会打开 memory target selector
- `/mcp`
  - 基础入口会打开 MCP server selector
- `/plugin`
  - 基础入口会打开 plugin selector
- `/rewind`
  - 会把 rewind 点渲染为 selector，并显示预览

### 当前已支持 action buttons 的命令

- `/memory show <target>`
  - 可直接返回 memory menu 或进入编辑
- `/mcp show <server_name>`
  - 可直接回到 MCP menu 或查看全部 tools
- `/plugin show <name>`
  - 可直接回到 plugin menu、reload 或查看 errors

### `/memory` 的交互升级

这一轮又把 `/memory` 往前推进了一层：

- `/memory`
  - 在 Textual 中会打开 memory selector
- `memory edit <target>` 现在不只是文本命令
- 在 Textual 中会打开 inline editor pane
- 保存后会直接写回 memory 文件
- 保存完成后会在 transcript 中追加一条 system 提示

这一步比之前的 action button 更接近原项目里 `/memory` 的“进入编辑流”体验。

### `/plugin` 与 `/mcp` 的交互升级

这一轮把 `/plugin` 和 `/mcp` 的基础入口也从“只看一屏文本”推进到了 selector 驱动的菜单流：

- `/plugin`
  - 在 Textual 中会列出当前插件、reload 入口、errors 入口
  - 每个插件都有预览区，可看到 scope / version / path / commands / skills
- `/mcp`
  - 在 Textual 中会列出当前 MCP servers 和 “All MCP Tools”
  - 每个 server 都有 transport / status / tool list 预览

这一步还不等于原项目的完整 settings/manage 页面，但已经明显更接近“先浏览、再下钻、再执行动作”的产品交互。

### Textual 主界面的继续原版化

这一轮继续把 Textual 的底层交互往原项目 `FullscreenLayout + PromptInput + PromptOverlay` 靠：

- composer 上方现在有独立的 prompt overlay
  - slash suggestions 不再只塞在输入框内部
  - overlay 右侧会显示 runtime / approval / tasks / remote notices
- transcript 现在支持：
  - sticky prompt
  - new messages pill
  - `Ctrl+O` 在 composer / transcript 间切换焦点
  - transcript 聚焦后输入 `/` 打开搜索
  - `n / N` 跳转搜索结果
- transcript 现在会在 `/clear`、`/resume`、`/rewind` 这类重写 session 的场景下正确整段重建，而不是只会 append

这一步还没有原项目那种完整虚拟滚动、message selector、scroll chrome 细节，但整体交互节奏已经明显更接近原版终端产品。

它们的行为现在是：

- 在 `prompt_toolkit` REPL 中
  - 仍然保持文本输出
- 在 Textual 中
  - 仍保留 transcript 兼容输出
  - 信息型命令会打开可滚动的信息面板
  - workflow 型命令会优先打开 selector
  - 编辑流会优先打开 inline editor

这一步的价值在于：

- 不需要推翻当前 slash command 架构
- 不会破坏 REPL / headless 路径
- 但能让 Textual 明显更像原项目里那种“命令驱动信息窗格”的产品体验
- 并且开始具备“看完信息直接点下一步”的 selector/workflow 感

新增测试：

- `tests/unit/test_textual_runtime.py`
  - 验证 `/status` 在 Textual runtime 中会触发 `info_dialog`
  - 验证 `/memory` 在 Textual runtime 中会触发 `selector_dialog`
- `tests/unit/test_commands.py`
  - 验证 `/memory`、`/mcp`、`/plugin` 会请求对应 selector dialog
- `tests/unit/test_textual_prompt_state.py`
  - 验证 prompt overlay suggestion 渲染
  - 验证 overlay notices 渲染
  - 验证 transcript search / sticky prompt helper

本轮验证：

- `python3 -m compileall claude_code_py/src/claude_code_py/ui claude_code_py/src/claude_code_py/commands claude_code_py/tests/unit/test_textual_runtime.py`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/pytest -q`
- `/Users/thy/miniforge3/envs/claude-code-py/bin/python scripts/release_check.py`

当前边界依然很重要：

- 现在的 Textual command pane 已经不只是“信息展示型”，但还没有做到原项目很多命令那种真正的多步交互流、分页、异步 UI workflow
- `rewind` 虽然已经有 selector UI，但还没有原项目更深的 restore-files / message-selector 体系
- `memory`
  - 现在已经有 selector + inline editor
  - 但还没有原项目那种外部 editor / 多文件 workflow / auto memory 的完整体验
- `plugin / mcp / hooks` 仍然没有完整 settings 页面和高级交互流程
- transcript 还没有原项目那种真正的虚拟滚动、scroll chrome 动画和更细的 message row 体系

所以这一轮最准确的描述是：

**Python 版已经从“命令可用”推进到“Textual 里有 prompt overlay、transcript 搜索、sticky prompt、selector、inline editor 的产品化命令面”，但距离原项目完整交互产品版仍然差在更细的消息组件、虚拟滚动、settings UI 和高级 runtime。**
