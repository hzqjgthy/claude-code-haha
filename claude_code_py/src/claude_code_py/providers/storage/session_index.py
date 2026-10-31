import sqlite3
from pathlib import Path

from claude_code_py.domain.sessions import SessionSummary


class SqliteSessionIndex:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER NOT NULL,
                    first_user_message TEXT,
                    last_user_message TEXT,
                    last_assistant_message TEXT,
                    transcript_path TEXT NOT NULL,
                    parent_session_id TEXT
                )
                """,
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_updated_at
                ON sessions(updated_at DESC)
                """,
            )

    def upsert(self, summary: SessionSummary) -> None:
        payload = summary.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id,
                    title,
                    status,
                    created_at,
                    updated_at,
                    message_count,
                    first_user_message,
                    last_user_message,
                    last_assistant_message,
                    transcript_path,
                    parent_session_id
                ) VALUES (
                    :session_id,
                    :title,
                    :status,
                    :created_at,
                    :updated_at,
                    :message_count,
                    :first_user_message,
                    :last_user_message,
                    :last_assistant_message,
                    :transcript_path,
                    :parent_session_id
                )
                ON CONFLICT(session_id) DO UPDATE SET
                    title = excluded.title,
                    status = excluded.status,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    message_count = excluded.message_count,
                    first_user_message = excluded.first_user_message,
                    last_user_message = excluded.last_user_message,
                    last_assistant_message = excluded.last_assistant_message,
                    transcript_path = excluded.transcript_path,
                    parent_session_id = excluded.parent_session_id
                """,
                payload,
            )

    def get(self, session_id: str) -> SessionSummary | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    session_id,
                    title,
                    status,
                    created_at,
                    updated_at,
                    message_count,
                    first_user_message,
                    last_user_message,
                    last_assistant_message,
                    transcript_path,
                    parent_session_id
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionSummary.model_validate(dict(row))

    def list_recent(self, *, limit: int = 20) -> list[SessionSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    session_id,
                    title,
                    status,
                    created_at,
                    updated_at,
                    message_count,
                    first_user_message,
                    last_user_message,
                    last_assistant_message,
                    transcript_path,
                    parent_session_id
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [SessionSummary.model_validate(dict(row)) for row in rows]

    def get_most_recent(self) -> SessionSummary | None:
        rows = self.list_recent(limit=1)
        return rows[0] if rows else None
