from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3


class SQLiteNetworkEnvelopeStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS network_envelope_receipts (
                    envelope_id TEXT PRIMARY KEY,
                    request_id TEXT UNIQUE,
                    sender_node_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    accepted_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_network_receipts_request_id "
                "ON network_envelope_receipts(request_id)"
            )

    def has_envelope_id(self, envelope_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM network_envelope_receipts WHERE envelope_id = ?",
                (envelope_id,),
            ).fetchone()
        return row is not None

    def has_request_id(self, request_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM network_envelope_receipts WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return row is not None

    def record_receipt(
        self,
        *,
        envelope_id: str,
        request_id: str | None,
        sender_node_id: str,
        message_type: str,
        payload_digest: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO network_envelope_receipts (
                    envelope_id, request_id, sender_node_id, message_type, payload_digest, accepted_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    envelope_id,
                    request_id,
                    sender_node_id,
                    message_type,
                    payload_digest,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
