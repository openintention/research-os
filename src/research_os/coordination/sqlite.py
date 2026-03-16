from __future__ import annotations

import sqlite3
from pathlib import Path

from research_os.domain.models import Lease, LeaseCommandAction


class SQLiteLeaseStore:
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
                CREATE TABLE IF NOT EXISTS leases (
                    lease_id TEXT PRIMARY KEY,
                    lease_schema TEXT NOT NULL,
                    lease_version INTEGER NOT NULL,
                    work_item_type TEXT NOT NULL,
                    participant_role TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    effort_id TEXT,
                    objective TEXT,
                    platform TEXT,
                    budget_seconds INTEGER,
                    planner_fingerprint TEXT NOT NULL,
                    holder_node_id TEXT,
                    holder_workspace_id TEXT,
                    status TEXT NOT NULL,
                    max_duration_seconds INTEGER NOT NULL,
                    renewal_count INTEGER NOT NULL DEFAULT 0,
                    acquired_at TEXT,
                    renewed_at TEXT,
                    released_at TEXT,
                    completed_at TEXT,
                    failed_at TEXT,
                    failure_reason TEXT,
                    observed_run_id TEXT,
                    observed_claim_id TEXT,
                    stale_completion INTEGER NOT NULL DEFAULT 0,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lease_command_receipts (
                    request_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    lease_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    PRIMARY KEY (request_id, action)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_leases_subject
                ON leases(work_item_type, participant_role, subject_type, subject_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_leases_status
                ON leases(status, expires_at)
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_leases_live_subject
                ON leases(work_item_type, participant_role, subject_type, subject_id)
                WHERE status IN ('acquired', 'renewed')
                """
            )

    def get_by_request(
        self,
        *,
        request_id: str,
        action: LeaseCommandAction,
        now_iso: str,
    ) -> Lease | None:
        with self._connect() as conn:
            self._expire_due_leases(conn, now_iso=now_iso)
            row = conn.execute(
                """
                SELECT leases.*
                FROM lease_command_receipts
                JOIN leases ON leases.lease_id = lease_command_receipts.lease_id
                WHERE lease_command_receipts.request_id = ? AND lease_command_receipts.action = ?
                """,
                (request_id, action.value),
            ).fetchone()
            if row is None:
                return None
            return self._lease_from_row(row)

    def get(self, lease_id: str, *, now_iso: str) -> Lease | None:
        with self._connect() as conn:
            self._expire_due_leases(conn, now_iso=now_iso)
            return self._get_with_connection(conn, lease_id)

    def find_live(
        self,
        *,
        work_item_type: str,
        participant_role: str,
        subject_type: str,
        subject_id: str,
        now_iso: str,
    ) -> Lease | None:
        with self._connect() as conn:
            self._expire_due_leases(conn, now_iso=now_iso)
            row = conn.execute(
                """
                SELECT *
                FROM leases
                WHERE work_item_type = ?
                  AND participant_role = ?
                  AND subject_type = ?
                  AND subject_id = ?
                  AND status IN ('acquired', 'renewed')
                LIMIT 1
                """,
                (work_item_type, participant_role, subject_type, subject_id),
            ).fetchone()
            if row is None:
                return None
            return self._lease_from_row(row)

    def insert(self, lease: Lease, *, request_id: str, action: LeaseCommandAction, now_iso: str) -> Lease:
        with self._connect() as conn:
            self._expire_due_leases(conn, now_iso=now_iso)
            conn.execute(
                """
                INSERT INTO leases (
                    lease_id, lease_schema, lease_version, work_item_type, participant_role,
                    subject_type, subject_id, effort_id, objective, platform, budget_seconds,
                    planner_fingerprint, holder_node_id, holder_workspace_id, status,
                    max_duration_seconds, renewal_count, acquired_at, renewed_at, released_at,
                    completed_at, failed_at, failure_reason, observed_run_id, observed_claim_id,
                    stale_completion, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._lease_params(lease),
            )
            self._record_receipt(conn, request_id=request_id, action=action, lease_id=lease.lease_id, now_iso=now_iso)
            return lease

    def save(self, lease: Lease, *, request_id: str, action: LeaseCommandAction, now_iso: str) -> Lease:
        with self._connect() as conn:
            self._expire_due_leases(conn, now_iso=now_iso)
            conn.execute(
                """
                UPDATE leases
                SET lease_schema = ?,
                    lease_version = ?,
                    work_item_type = ?,
                    participant_role = ?,
                    subject_type = ?,
                    subject_id = ?,
                    effort_id = ?,
                    objective = ?,
                    platform = ?,
                    budget_seconds = ?,
                    planner_fingerprint = ?,
                    holder_node_id = ?,
                    holder_workspace_id = ?,
                    status = ?,
                    max_duration_seconds = ?,
                    renewal_count = ?,
                    acquired_at = ?,
                    renewed_at = ?,
                    released_at = ?,
                    completed_at = ?,
                    failed_at = ?,
                    failure_reason = ?,
                    observed_run_id = ?,
                    observed_claim_id = ?,
                    stale_completion = ?,
                    expires_at = ?
                WHERE lease_id = ?
                """,
                (
                    lease.lease_schema,
                    lease.lease_version,
                    lease.work_item_type.value,
                    lease.participant_role.value,
                    lease.subject_type.value,
                    lease.subject_id,
                    lease.effort_id,
                    lease.objective,
                    lease.platform,
                    lease.budget_seconds,
                    lease.planner_fingerprint,
                    lease.holder_node_id,
                    lease.holder_workspace_id,
                    lease.status.value,
                    lease.max_duration_seconds,
                    lease.renewal_count,
                    self._isoformat(lease.acquired_at),
                    self._isoformat(lease.renewed_at),
                    self._isoformat(lease.released_at),
                    self._isoformat(lease.completed_at),
                    self._isoformat(lease.failed_at),
                    lease.failure_reason,
                    lease.observed_run_id,
                    lease.observed_claim_id,
                    1 if lease.stale_completion else 0,
                    lease.expires_at.isoformat(),
                    lease.lease_id,
                ),
            )
            self._record_receipt(conn, request_id=request_id, action=action, lease_id=lease.lease_id, now_iso=now_iso)
            return lease

    def _get_with_connection(self, conn: sqlite3.Connection, lease_id: str) -> Lease | None:
        row = conn.execute("SELECT * FROM leases WHERE lease_id = ?", (lease_id,)).fetchone()
        if row is None:
            return None
        return self._lease_from_row(row)

    def _expire_due_leases(self, conn: sqlite3.Connection, *, now_iso: str) -> None:
        conn.execute(
            """
            UPDATE leases
            SET status = 'expired'
            WHERE status IN ('acquired', 'renewed')
              AND expires_at <= ?
            """,
            (now_iso,),
        )

    def _record_receipt(
        self,
        conn: sqlite3.Connection,
        *,
        request_id: str,
        action: LeaseCommandAction,
        lease_id: str,
        now_iso: str,
    ) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO lease_command_receipts (request_id, action, lease_id, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (request_id, action.value, lease_id, now_iso),
        )

    def _lease_from_row(self, row: sqlite3.Row) -> Lease:
        return Lease.model_validate(
            {
                "lease_id": row["lease_id"],
                "lease_schema": row["lease_schema"],
                "lease_version": row["lease_version"],
                "work_item_type": row["work_item_type"],
                "participant_role": row["participant_role"],
                "subject_type": row["subject_type"],
                "subject_id": row["subject_id"],
                "effort_id": row["effort_id"],
                "objective": row["objective"],
                "platform": row["platform"],
                "budget_seconds": row["budget_seconds"],
                "planner_fingerprint": row["planner_fingerprint"],
                "holder_node_id": row["holder_node_id"],
                "holder_workspace_id": row["holder_workspace_id"],
                "status": row["status"],
                "max_duration_seconds": row["max_duration_seconds"],
                "renewal_count": row["renewal_count"],
                "acquired_at": row["acquired_at"],
                "renewed_at": row["renewed_at"],
                "released_at": row["released_at"],
                "completed_at": row["completed_at"],
                "failed_at": row["failed_at"],
                "failure_reason": row["failure_reason"],
                "observed_run_id": row["observed_run_id"],
                "observed_claim_id": row["observed_claim_id"],
                "stale_completion": bool(row["stale_completion"]),
                "expires_at": row["expires_at"],
            }
        )

    def _lease_params(self, lease: Lease) -> tuple[object, ...]:
        return (
            lease.lease_id,
            lease.lease_schema,
            lease.lease_version,
            lease.work_item_type.value,
            lease.participant_role.value,
            lease.subject_type.value,
            lease.subject_id,
            lease.effort_id,
            lease.objective,
            lease.platform,
            lease.budget_seconds,
            lease.planner_fingerprint,
            lease.holder_node_id,
            lease.holder_workspace_id,
            lease.status.value,
            lease.max_duration_seconds,
            lease.renewal_count,
            self._isoformat(lease.acquired_at),
            self._isoformat(lease.renewed_at),
            self._isoformat(lease.released_at),
            self._isoformat(lease.completed_at),
            self._isoformat(lease.failed_at),
            lease.failure_reason,
            lease.observed_run_id,
            lease.observed_claim_id,
            1 if lease.stale_completion else 0,
            lease.expires_at.isoformat(),
        )

    def _isoformat(self, value: object) -> str | None:
        if value is None:
            return None
        return value.isoformat()
