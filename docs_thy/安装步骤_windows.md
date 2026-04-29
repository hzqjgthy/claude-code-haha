# Windows 安装步骤

适用环境：Windows 10 / 11。Bun 官方要求 Windows 10 1809 或更高版本。推荐使用 PowerShell 7，也兼容 Windows PowerShell 5.1。

## 1. 安装前置依赖

需要：

- Bun >= 1.1
- Node.js >= 18
- Git for Windows（项目在 Windows 下需要 Git Bash）

### 安装 Git for Windows

推荐直接使用 `winget`：

```powershell
winget install --id Git.Git -e --source winget
```

安装完成后，重新打开终端，确认：

```powershell
git --version
```

如果你已经安装了 Git，但不在 PATH 中，也可以手动设置：

```powershell
$env:CLAUDE_CODE_GIT_BASH_PATH = 'C:\Program Files\Git\bin\bash.exe'
```

### 安装 Bun

官方 PowerShell 安装方式：

```powershell
powershell -c "irm bun.sh/install.ps1 | iex"
```

安装完成后，重新打开终端，确认：

```powershell
bun --version
node --version
```

## 2. 安装项目依赖

在项目根目录执行：

```powershell
npm install
```

## 3. 配置环境变量

复制配置模板：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`。

首次启动建议优先填写 `ANTHROPIC_AUTH_TOKEN`，不要只填 `ANTHROPIC_API_KEY`，这样能避免首次初始化时触发地域检测问题。首次登录完成后，如果你有自己的兼容接口需求，再按原有方式调整即可。

## 4. 启动

Windows 入口脚本：

```powershell
.\bin\claude-haha.cmd
```

无头模式：

```powershell
.\bin\claude-haha.cmd -p "your prompt here"
```

查看帮助：

```powershell
.\bin\claude-haha.cmd --help
```

管道输入：

```powershell
'explain this code' | .\bin\claude-haha.cmd -p
```

## 5. 可选模式

启用 recovery CLI：

```powershell
$env:CLAUDE_CODE_FORCE_RECOVERY_CLI = '1'
.\bin\claude-haha.cmd
Remove-Item Env:CLAUDE_CODE_FORCE_RECOVERY_CLI
```

导出 system prompt：

```powershell
$env:CLAUDE_CODE_ENABLE_DUMP_SYSTEM_PROMPT = '1'
.\bin\claude-haha.cmd --dump-system-prompt
Remove-Item Env:CLAUDE_CODE_ENABLE_DUMP_SYSTEM_PROMPT
```

## 6. 常见问题

### 提示找不到 `bun`

说明 Bun 没安装成功，或者新安装后终端还没重开。先执行：

```powershell
bun --version
```

如果命令不存在，重新安装 Bun 并重开 PowerShell。

### 提示找不到 Git Bash

这个项目在 Windows 下会依赖 Git Bash。先确认：

```powershell
git --version
```

如果 Git 已安装但项目仍提示找不到 `bash.exe`，手动指定：

```powershell
$env:CLAUDE_CODE_GIT_BASH_PATH = 'C:\Program Files\Git\bin\bash.exe'
.\bin\claude-haha.cmd
```
