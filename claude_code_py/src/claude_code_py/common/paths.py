from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    root: Path
    src_root: Path
    package_root: Path
    docs_dir: Path
    tests_dir: Path
    scripts_dir: Path
    data_dir: Path
    sessions_dir: Path
    session_index_path: Path
    env_file: Path


def build_project_paths() -> ProjectPaths:
    root = Path(__file__).resolve().parents[3]
    src_root = root / "src"
    package_root = src_root / "claude_code_py"
    return ProjectPaths(
        root=root,
        src_root=src_root,
        package_root=package_root,
        docs_dir=root / "docs",
        tests_dir=root / "tests",
        scripts_dir=root / "scripts",
        data_dir=root / ".local" / "state",
        sessions_dir=root / ".local" / "state" / "sessions",
        session_index_path=root / ".local" / "state" / "session_index.sqlite3",
        env_file=root / ".env",
    )
