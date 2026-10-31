from pathlib import Path

from claude_code_py.tools.base import ToolContext

FILE_CONTEXT_METADATA_KEY = "file_context_paths"
MAX_TRACKED_FILES = 200


def remember_file_context_path(context: ToolContext, file_path: Path) -> None:
    existing = context.metadata.get(FILE_CONTEXT_METADATA_KEY, [])
    if not isinstance(existing, list):
        existing = []

    normalized = str(file_path)
    deduped = [value for value in existing if isinstance(value, str) and value != normalized]
    deduped.append(normalized)
    context.metadata[FILE_CONTEXT_METADATA_KEY] = deduped[-MAX_TRACKED_FILES:]


def list_file_context_paths(context: ToolContext) -> list[Path]:
    values = context.metadata.get(FILE_CONTEXT_METADATA_KEY, [])
    if not isinstance(values, list):
        return []
    paths: list[Path] = []
    for value in values:
        if not isinstance(value, str):
            continue
        paths.append(Path(value))
    return paths
