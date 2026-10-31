from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(command: list[str], *, cwd: Path) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    run_command(
        [sys.executable, "-m", "compileall", "src", "tests", "scripts"], cwd=root
    )
    run_command([sys.executable, "-m", "pytest", "-q"], cwd=root)
    run_command([sys.executable, "scripts/parity_check.py"], cwd=root)
    run_command(
        [sys.executable, "scripts/stress_tool_loop.py", "--rounds", "18"], cwd=root
    )
    run_command([sys.executable, "-m", "claude_code_py", "--help"], cwd=root)
    run_command([sys.executable, "-m", "claude_code_py", "doctor"], cwd=root)

    with tempfile.TemporaryDirectory(prefix="claude-code-py-wheel-") as dist_dir:
        run_command(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                ".",
                "--no-deps",
                "-w",
                dist_dir,
            ],
            cwd=root,
        )
        built = sorted(Path(dist_dir).glob("*.whl"))
        if not built:
            raise RuntimeError("wheel build completed without producing a wheel file")
        print(f"built_wheel={built[0].name}")

    editable_info = root / "src" / "claude_code_py" / "__main__.py"
    if not editable_info.exists():
        raise RuntimeError("package smoke check failed: missing __main__.py")
    print("release_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
