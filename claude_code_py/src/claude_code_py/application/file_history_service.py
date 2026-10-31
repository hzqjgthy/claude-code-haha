from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from claude_code_py.common.json import from_json, to_json


def _now_utc() -> datetime:
    return datetime.now(UTC)


class FileSnapshotEntry(BaseModel):
    path: str
    existed: bool
    content: str | None = None


class FileTurnSnapshot(BaseModel):
    turn_id: str
    created_at: datetime = Field(default_factory=_now_utc)
    files: dict[str, FileSnapshotEntry] = Field(default_factory=dict)


class FileHistoryDocument(BaseModel):
    session_id: str
    snapshots: list[FileTurnSnapshot] = Field(default_factory=list)


class FileRestoreReport(BaseModel):
    restored_files: int = 0
    deleted_files: int = 0
    snapshot_file_count: int = 0


class FileHistoryService:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def history_path(self, session_id: str) -> Path:
        return self._base_dir / f"{session_id}.json"

    def load(self, session_id: str) -> FileHistoryDocument:
        path = self.history_path(session_id)
        if not path.exists():
            return FileHistoryDocument(session_id=session_id)
        try:
            raw = from_json(path.read_text(encoding="utf-8"))
        except Exception:
            return FileHistoryDocument(session_id=session_id)
        if not isinstance(raw, dict):
            return FileHistoryDocument(session_id=session_id)
        try:
            return FileHistoryDocument.model_validate(raw)
        except Exception:
            return FileHistoryDocument(session_id=session_id)

    def save(self, document: FileHistoryDocument) -> None:
        path = self.history_path(document.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            to_json(document.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )

    def snapshot_count(self, session_id: str) -> int:
        return len(self.load(session_id).snapshots)

    def snapshot_for_turn(
        self,
        session_id: str,
        turn_id: str,
    ) -> FileTurnSnapshot | None:
        document = self.load(session_id)
        for snapshot in document.snapshots:
            if snapshot.turn_id == turn_id:
                return snapshot
        return None

    def capture_before_mutation(
        self,
        *,
        session_id: str,
        turn_id: str,
        file_path: Path,
    ) -> None:
        document = self.load(session_id)
        snapshot = self._ensure_snapshot(document, turn_id)
        key = str(file_path.resolve())
        if key in snapshot.files:
            return
        entry = self._read_entry(file_path)
        snapshot.files[key] = entry
        self.save(document)

    def restore_turn(
        self,
        *,
        session_id: str,
        turn_id: str,
        allowed_roots: list[Path],
    ) -> FileRestoreReport | None:
        snapshot = self.snapshot_for_turn(session_id, turn_id)
        if snapshot is None:
            return None
        report = FileRestoreReport(snapshot_file_count=len(snapshot.files))
        normalized_roots = [root.resolve() for root in allowed_roots]
        for entry in snapshot.files.values():
            path = Path(entry.path).resolve()
            if not _path_within_roots(path, normalized_roots):
                continue
            if entry.existed:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(entry.content or "", encoding="utf-8")
                report.restored_files += 1
                continue
            if path.exists():
                path.unlink()
                report.deleted_files += 1
        return report

    def prune_to_turn_ids(
        self,
        session_id: str,
        active_turn_ids: set[str],
    ) -> int:
        document = self.load(session_id)
        original = len(document.snapshots)
        document.snapshots = [
            snapshot for snapshot in document.snapshots if snapshot.turn_id in active_turn_ids
        ]
        removed = original - len(document.snapshots)
        if removed:
            self.save(document)
        return removed

    def latest_snapshot(self, session_id: str) -> FileTurnSnapshot | None:
        document = self.load(session_id)
        return document.snapshots[-1] if document.snapshots else None

    @staticmethod
    def _ensure_snapshot(
        document: FileHistoryDocument,
        turn_id: str,
    ) -> FileTurnSnapshot:
        for snapshot in document.snapshots:
            if snapshot.turn_id == turn_id:
                return snapshot
        snapshot = FileTurnSnapshot(turn_id=turn_id)
        document.snapshots.append(snapshot)
        return snapshot

    @staticmethod
    def _read_entry(file_path: Path) -> FileSnapshotEntry:
        if not file_path.exists():
            return FileSnapshotEntry(path=str(file_path.resolve()), existed=False)
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            content = None
        return FileSnapshotEntry(
            path=str(file_path.resolve()),
            existed=True,
            content=content,
        )


def _path_within_roots(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False
