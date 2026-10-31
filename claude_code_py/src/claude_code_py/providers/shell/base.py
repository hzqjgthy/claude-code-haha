from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ShellCommandResult:
    command: str
    cwd: Path
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class ShellProvider(ABC):
    @abstractmethod
    def run(self, command: str, *, cwd: Path, timeout: int | None = None) -> ShellCommandResult:
        raise NotImplementedError
