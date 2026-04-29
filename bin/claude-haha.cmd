@echo off
setlocal EnableExtensions

REM Resolve the repository root from the bin directory.
for %%I in ("%~dp0..") do set "ROOT_DIR=%%~fI"

where bun >nul 2>nul
if errorlevel 1 (
  >&2 echo [claude-haha] Bun was not found in PATH.
  >&2 echo [claude-haha] Install Bun first, then reopen the terminal:
  >&2 echo [claude-haha] https://bun.sh/docs/installation
  exit /b 1
)

set "ENTRYPOINT=.\src\entrypoints\cli.tsx"
if "%CLAUDE_CODE_FORCE_RECOVERY_CLI%"=="1" (
  set "ENTRYPOINT=.\src\localRecoveryCli.ts"
)

pushd "%ROOT_DIR%" >nul
if errorlevel 1 (
  >&2 echo [claude-haha] Failed to enter project root: %ROOT_DIR%
  exit /b 1
)

if "%CLAUDE_CODE_ENABLE_DUMP_SYSTEM_PROMPT%"=="1" (
  bun --env-file=.env --feature=DUMP_SYSTEM_PROMPT "%ENTRYPOINT%" %*
) else (
  bun --env-file=.env "%ENTRYPOINT%" %*
)

set "EXIT_CODE=%ERRORLEVEL%"
popd >nul
exit /b %EXIT_CODE%
