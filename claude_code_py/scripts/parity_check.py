from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, "-m", "pytest", "tests/parity", "-q"]
    print(f"$ {' '.join(command)}")
    completed = subprocess.run(command, cwd=root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(run())
