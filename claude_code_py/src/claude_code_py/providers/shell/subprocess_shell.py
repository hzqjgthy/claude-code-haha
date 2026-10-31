from pathlib import Path
import subprocess

from claude_code_py.providers.shell.base import ShellCommandResult, ShellProvider


class SubprocessShellProvider(ShellProvider):
    def run(self, command: str, *, cwd: Path, timeout: int | None = None) -> ShellCommandResult:
        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            return ShellCommandResult(
                command=command,
                cwd=cwd,
                exit_code=124,
                stdout=stdout,
                stderr=stderr or "Command timed out.",
                timed_out=True,
            )

        return ShellCommandResult(
            command=command,
            cwd=cwd,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            timed_out=False,
        )
