from __future__ import annotations

import json
import sqlite3
from typing import Iterable

from research_os.domain.models import ClaimStatus, ClaimSummary, EventEnvelope, EventKind
from research_os.projections.materialized import SQLiteProjection

CLAIM_PROJECTION_TABLE = "claim_projection_summaries"


def build_claim_summaries(
    events: Iterable[EventEnvelope],
    *,
    objective: str | None = None,
    platform: str | None = None,
) -> list[ClaimSummary]:
    claim_map: dict[str, ClaimSummary] = {}

    for event in events:
        payload = event.payload
        if event.kind == EventKind.CLAIM_ASSERTED:
            if objective and payload.get("objective") != objective:
                continue
            if platform and payload.get("platform") != platform:
                continue

            claim_id = payload["claim_id"]
            claim_map[claim_id] = ClaimSummary(
                claim_id=claim_id,
                workspace_id=event.workspace_id,
                statement=payload["statement"],
                claim_type=payload["claim_type"],
                candidate_snapshot_id=payload["candidate_snapshot_id"],
                baseline_snapshot_id=payload.get("baseline_snapshot_id"),
                objective=payload["objective"],
                platform=payload["platform"],
                metric_name=payload.get("metric_name"),
                delta=payload.get("delta"),
                confidence=payload.get("confidence"),
                evidence_run_ids=list(payload.get("evidence_run_ids", [])),
                tags=event.tags,
                updated_at=event.occurred_at,
            )
        elif event.kind in {EventKind.CLAIM_REPRODUCED, EventKind.CLAIM_CONTRADICTED}:
            claim_id = payload["claim_id"]
            summary = claim_map.get(claim_id)
            if summary is None:
                continue
            if event.kind == EventKind.CLAIM_REPRODUCED:
                summary.support_count += 1
            else:
                summary.contradiction_count += 1
            evidence_run_id = payload.get("evidence_run_id")
            if evidence_run_id and evidence_run_id not in summary.evidence_run_ids:
                summary.evidence_run_ids.append(evidence_run_id)
            summary.updated_at = event.occurred_at

    for summary in claim_map.values():
        summary.status = _derive_status(summary)

    return sorted(claim_map.values(), key=lambda item: (item.updated_at, item.claim_id), reverse=True)


def init_claim_projection_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {CLAIM_PROJECTION_TABLE} (
            claim_id TEXT PRIMARY KEY,
            workspace_id TEXT,
            statement TEXT NOT NULL,
            claim_type TEXT NOT NULL,
            candidate_snapshot_id TEXT NOT NULL,
            baseline_snapshot_id TEXT,
            objective TEXT NOT NULL,
            platform TEXT NOT NULL,
            metric_name TEXT,
            delta REAL,
            confidence REAL,
            evidence_run_ids_json TEXT NOT NULL,
            support_count INTEGER NOT NULL DEFAULT 0,
            contradiction_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{CLAIM_PROJECTION_TABLE}_lookup
        ON {CLAIM_PROJECTION_TABLE}(objective, platform, updated_at)
        """
    )


def reset_claim_projection(conn: sqlite3.Connection) -> None:
    conn.execute(f"DELETE FROM {CLAIM_PROJECTION_TABLE}")


def apply_claim_projection_event(conn: sqlite3.Connection, event: EventEnvelope) -> None:
    payload = event.payload

    if event.kind == EventKind.CLAIM_ASSERTED:
        conn.execute(
            f"""
            INSERT INTO {CLAIM_PROJECTION_TABLE} (
                claim_id,
                workspace_id,
                statement,
                claim_type,
                candidate_snapshot_id,
                baseline_snapshot_id,
                objective,
                platform,
                metric_name,
                delta,
                confidence,
                evidence_run_ids_json,
                support_count,
                contradiction_count,
                status,
                tags_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?)
            ON CONFLICT(claim_id) DO UPDATE SET
                workspace_id = excluded.workspace_id,
                statement = excluded.statement,
                claim_type = excluded.claim_type,
                candidate_snapshot_id = excluded.candidate_snapshot_id,
                baseline_snapshot_id = excluded.baseline_snapshot_id,
                objective = excluded.objective,
                platform = excluded.platform,
                metric_name = excluded.metric_name,
                delta = excluded.delta,
                confidence = excluded.confidence,
                evidence_run_ids_json = excluded.evidence_run_ids_json,
                support_count = 0,
                contradiction_count = 0,
                status = excluded.status,
                tags_json = excluded.tags_json,
                updated_at = excluded.updated_at
            """,
            (
                payload["claim_id"],
                event.workspace_id,
                payload["statement"],
                payload["claim_type"],
                payload["candidate_snapshot_id"],
                payload.get("baseline_snapshot_id"),
                payload["objective"],
                payload["platform"],
                payload.get("metric_name"),
                payload.get("delta"),
                payload.get("confidence"),
                json.dumps(list(payload.get("evidence_run_ids", [])), sort_keys=True),
                ClaimStatus.PENDING.value,
                json.dumps(event.tags, sort_keys=True),
                event.occurred_at.isoformat(),
            ),
        )
        return

    if event.kind in {EventKind.CLAIM_REPRODUCED, EventKind.CLAIM_CONTRADICTED}:
        _update_claim_counter(
            conn,
            claim_id=payload["claim_id"],
            evidence_run_id=payload.get("evidence_run_id"),
            kind=event.kind,
            updated_at=event.occurred_at.isoformat(),
        )


def load_claim_summaries(
    conn: sqlite3.Connection,
    *,
    objective: str | None = None,
    platform: str | None = None,
) -> list[ClaimSummary]:
    clauses: list[str] = []
    params: list[str] = []

    if objective:
        clauses.append("objective = ?")
        params.append(objective)
    if platform:
        clauses.append("platform = ?")
        params.append(platform)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"""
        SELECT *
        FROM {CLAIM_PROJECTION_TABLE}
        {where}
        ORDER BY updated_at DESC, claim_id DESC
        """,
        params,
    ).fetchall()

    return [
        ClaimSummary(
            claim_id=row["claim_id"],
            workspace_id=row["workspace_id"],
            statement=row["statement"],
            claim_type=row["claim_type"],
            candidate_snapshot_id=row["candidate_snapshot_id"],
            baseline_snapshot_id=row["baseline_snapshot_id"],
            objective=row["objective"],
            platform=row["platform"],
            metric_name=row["metric_name"],
            delta=row["delta"],
            confidence=row["confidence"],
            evidence_run_ids=json.loads(row["evidence_run_ids_json"]),
            support_count=row["support_count"],
            contradiction_count=row["contradiction_count"],
            status=ClaimStatus(row["status"]),
            tags=json.loads(row["tags_json"]),
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


CLAIMS_PROJECTION = SQLiteProjection(
    name="claims",
    schema_version=1,
    checksum_source="claim_projection_summaries_v1",
    init_schema=init_claim_projection_schema,
    reset=reset_claim_projection,
    apply=apply_claim_projection_event,
)


def _derive_status(summary: ClaimSummary) -> ClaimStatus:
    if summary.contradiction_count > 0:
        return ClaimStatus.CONTESTED
    if summary.support_count > 0:
        return ClaimStatus.SUPPORTED
    return ClaimStatus.PENDING


def _update_claim_counter(
    conn: sqlite3.Connection,
    *,
    claim_id: str,
    evidence_run_id: str | None,
    kind: EventKind,
    updated_at: str,
) -> None:
    row = conn.execute(
        f"""
        SELECT evidence_run_ids_json, support_count, contradiction_count
        FROM {CLAIM_PROJECTION_TABLE}
        WHERE claim_id = ?
        """,
        (claim_id,),
    ).fetchone()
    if row is None:
        return

    evidence_run_ids = json.loads(row["evidence_run_ids_json"])
    if evidence_run_id and evidence_run_id not in evidence_run_ids:
        evidence_run_ids.append(evidence_run_id)

    support_count = row["support_count"] + (1 if kind == EventKind.CLAIM_REPRODUCED else 0)
    contradiction_count = row["contradiction_count"] + (
        1 if kind == EventKind.CLAIM_CONTRADICTED else 0
    )

    conn.execute(
        f"""
        UPDATE {CLAIM_PROJECTION_TABLE}
        SET evidence_run_ids_json = ?,
            support_count = ?,
            contradiction_count = ?,
            status = ?,
            updated_at = ?
        WHERE claim_id = ?
        """,
        (
            json.dumps(evidence_run_ids, sort_keys=True),
            support_count,
            contradiction_count,
            _derive_status_from_counts(
                support_count=support_count,
                contradiction_count=contradiction_count,
            ).value,
            updated_at,
            claim_id,
        ),
    )


def _derive_status_from_counts(*, support_count: int, contradiction_count: int) -> ClaimStatus:
    if contradiction_count > 0:
        return ClaimStatus.CONTESTED
    if support_count > 0:
        return ClaimStatus.SUPPORTED
    return ClaimStatus.PENDING
