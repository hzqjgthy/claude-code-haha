"""Shell execution adapters."""

from claude_code_py.providers.shell.base import ShellCommandResult, ShellProvider
from claude_code_py.providers.shell.subprocess_shell import SubprocessShellProvider

__all__ = [
    "ShellCommandResult",
    "ShellProvider",
    "SubprocessShellProvider",
]
