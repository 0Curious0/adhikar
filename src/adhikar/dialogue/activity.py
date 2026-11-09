import sqlite3
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ActivityEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    scheme_id: str
    eligibility_status: str
    created_at: str
    """ISO 8601 UTC timestamp — stored as text (not a DB-native datetime type) to match
    SQLiteProfileStore's plain-column style; callers that need a datetime can parse it."""


class ActivityLogStore(ABC):
    @abstractmethod
    def log(self, user_id: str, *, scheme_id: str, eligibility_status: str) -> None:
        """Record one "a scheme newly became this user's topic" event."""

    @abstractmethod
    def recent(self, user_id: str, *, limit: int = 10) -> list[ActivityEntry]:
        """Return `user_id`'s most recent entries, newest first."""


class SQLiteActivityLogStore(ActivityLogStore):
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                scheme_id TEXT NOT NULL,
                eligibility_status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def log(self, user_id: str, *, scheme_id: str, eligibility_status: str) -> None:
        self._conn.execute(
            "INSERT INTO activity_log (user_id, scheme_id, eligibility_status, created_at) VALUES (?, ?, ?, ?)",
            (user_id, scheme_id, eligibility_status, datetime.now(UTC).isoformat()),
        )
        self._conn.commit()

    def recent(self, user_id: str, *, limit: int = 10) -> list[ActivityEntry]:
        rows = self._conn.execute(
            "SELECT scheme_id, eligibility_status, created_at FROM activity_log "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            ActivityEntry(scheme_id=scheme_id, eligibility_status=eligibility_status, created_at=created_at)
            for scheme_id, eligibility_status, created_at in rows
        ]

    def close(self) -> None:
        self._conn.close()
