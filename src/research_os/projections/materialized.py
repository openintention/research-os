from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from research_os.domain.models import EventEnvelope

PROJECTION_METADATA_TABLE = "projection_metadata"


def init_projection_metadata_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {PROJECTION_METADATA_TABLE} (
            projection_name TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL,
            checksum TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


@dataclass(frozen=True, slots=True)
class SQLiteProjection:
    name: str
    schema_version: int
    checksum_source: str
    init_schema: Callable[[sqlite3.Connection], None]
    reset: Callable[[sqlite3.Connection], None]
    apply: Callable[[sqlite3.Connection, EventEnvelope], None]

    @property
    def checksum(self) -> str:
        return hashlib.sha256(
            f"{self.name}:{self.schema_version}:{self.checksum_source}".encode("utf-8")
        ).hexdigest()

    def is_current(self, conn: sqlite3.Connection) -> bool:
        row = conn.execute(
            f"""
            SELECT schema_version, checksum
            FROM {PROJECTION_METADATA_TABLE}
            WHERE projection_name = ?
            """,
            (self.name,),
        ).fetchone()
        return row is not None and row["schema_version"] == self.schema_version and row["checksum"] == self.checksum

    def record_metadata(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            f"""
            INSERT INTO {PROJECTION_METADATA_TABLE} (
                projection_name, schema_version, checksum, updated_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(projection_name) DO UPDATE SET
                schema_version = excluded.schema_version,
                checksum = excluded.checksum,
                updated_at = excluded.updated_at
            """,
            (
                self.name,
                self.schema_version,
                self.checksum,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def rebuild(self, conn: sqlite3.Connection, events: Iterable[EventEnvelope]) -> None:
        self.reset(conn)
        for event in events:
            self.apply(conn, event)
        self.record_metadata(conn)
