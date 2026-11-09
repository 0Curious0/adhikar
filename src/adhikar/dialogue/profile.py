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
    last_asked_fields: list[str] = []
    """Which fields the assistant's last reply actually asked about, if it was a MISSING_FIELDS
    question — empty otherwise (eligible/not-eligible/grievance/no-scheme-pinned replies all
    clear it). Fed back into `classify_intent`/`extract_entities` on the next turn — without it,
    neither call has any way to tell a short or vague reply ("yes", "I don't have one") is
    answering the question just asked rather than being a fresh, unrelated statement; that gap
    was the direct cause of fact-filling turns silently going nowhere (see
    `Orchestrator._build_eligibility_message`'s asked-fields bookkeeping)."""


def merge_facts(profile: UserProfile, new_facts: dict[str, Any]) -> UserProfile:
    return profile.model_copy(update={"facts": {**profile.facts, **new_facts}})


def pin_scheme(profile: UserProfile, scheme_id: str) -> UserProfile:
    return profile.model_copy(update={"pinned_scheme_id": scheme_id})


def set_last_asked_fields(profile: UserProfile, fields: list[str]) -> UserProfile:
    return profile.model_copy(update={"last_asked_fields": fields})


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
                pinned_scheme_id TEXT,
                last_asked_fields TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        # Pre-existing databases from before last_asked_fields existed won't have the column —
        # SQLite's ALTER TABLE ADD COLUMN is the standard way to migrate an existing table in
        # place without a new dependency or a destructive rebuild.
        existing_columns = {row[1] for row in self._conn.execute("PRAGMA table_info(user_profiles)")}
        if "last_asked_fields" not in existing_columns:
            self._conn.execute("ALTER TABLE user_profiles ADD COLUMN last_asked_fields TEXT NOT NULL DEFAULT '[]'")
        self._conn.commit()

    def get(self, user_id: str) -> UserProfile:
        row = self._conn.execute(
            "SELECT facts, pinned_scheme_id, last_asked_fields FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return UserProfile(user_id=user_id)
        facts_json, pinned_scheme_id, last_asked_fields_json = row
        return UserProfile(
            user_id=user_id,
            facts=json.loads(facts_json),
            pinned_scheme_id=pinned_scheme_id,
            last_asked_fields=json.loads(last_asked_fields_json),
        )

    def save(self, profile: UserProfile) -> None:
        self._conn.execute(
            """
            INSERT INTO user_profiles (user_id, facts, pinned_scheme_id, last_asked_fields) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                facts = excluded.facts,
                pinned_scheme_id = excluded.pinned_scheme_id,
                last_asked_fields = excluded.last_asked_fields
            """,
            (profile.user_id, json.dumps(profile.facts), profile.pinned_scheme_id, json.dumps(profile.last_asked_fields)),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
