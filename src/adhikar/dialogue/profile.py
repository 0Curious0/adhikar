import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class UserProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str
    facts: dict[str, Any] = {}
    pinned_scheme_id: str | None = None


def merge_facts(profile: UserProfile, new_facts: dict[str, Any]) -> UserProfile:
    return profile.model_copy(update={"facts": {**profile.facts, **new_facts}})


def pin_scheme(profile: UserProfile, scheme_id: str) -> UserProfile:
    return profile.model_copy(update={"pinned_scheme_id": scheme_id})


class ProfileStore(ABC):
    @abstractmethod
    def get(self, user_id: str) -> UserProfile:
        """Return the stored profile for `user_id`, or an empty one if none exists yet."""

    @abstractmethod
    def save(self, profile: UserProfile) -> None:
        """Persist `profile`, replacing whatever was stored for its `user_id`."""


class SQLiteProfileStore(ProfileStore):
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                facts TEXT NOT NULL,
                pinned_scheme_id TEXT
            )
            """
        )
        self._conn.commit()

    def get(self, user_id: str) -> UserProfile:
        row = self._conn.execute(
            "SELECT facts, pinned_scheme_id FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return UserProfile(user_id=user_id)
        facts_json, pinned_scheme_id = row
        return UserProfile(user_id=user_id, facts=json.loads(facts_json), pinned_scheme_id=pinned_scheme_id)

    def save(self, profile: UserProfile) -> None:
        self._conn.execute(
            """
            INSERT INTO user_profiles (user_id, facts, pinned_scheme_id) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                facts = excluded.facts,
                pinned_scheme_id = excluded.pinned_scheme_id
            """,
            (profile.user_id, json.dumps(profile.facts), profile.pinned_scheme_id),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()