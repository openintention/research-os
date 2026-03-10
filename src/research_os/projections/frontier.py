from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from typing import Iterable

from research_os.domain.models import EventEnvelope, EventKind, FrontierMember, FrontierView
from research_os.projections.claims import build_claim_summaries
from research_os.projections.materialized import SQLiteProjection

FRONTIER_MEMBER_TABLE = "frontier_projection_members"
FRONTIER_CLAIM_TABLE = "frontier_projection_claims"


@dataclass(slots=True)
class _RunCandidate:
    workspace_id: str | None
    run_id: str
    snapshot_id: str
    objective: str
    platform: str
    budget_seconds: int
    metric_name: str
    metric_value: float
    direction: str
    last_updated_at: object
    tags: dict[str, str]


def build_frontier(
    events: Iterable[EventEnvelope],
    *,
    objective: str,
    platform: str,
    budget_seconds: int | None = None,
    limit: int = 10,
) -> FrontierView:
    best_by_snapshot: dict[str, _RunCandidate] = {}

    for event in events:
        if event.kind != EventKind.RUN_COMPLETED:
            continue

        payload = event.payload
        if payload.get("status") != "success":
            continue
        if payload.get("objective") != objective:
            continue
        if payload.get("platform") != platform:
            continue
        if budget_seconds is not None and int(payload.get("budget_seconds", 0)) != budget_seconds:
            continue

        candidate = _RunCandidate(
            workspace_id=event.workspace_id,
            run_id=payload["run_id"],
            snapshot_id=payload["snapshot_id"],
            objective=payload["objective"],
            platform=payload["platform"],
            budget_seconds=int(payload["budget_seconds"]),
            metric_name=payload["metric_name"],
            metric_value=float(payload["metric_value"]),
            direction=payload["direction"],
            last_updated_at=event.occurred_at,
            tags=event.tags,
        )
        existing = best_by_snapshot.get(candidate.snapshot_id)
        if existing is None or _is_better(candidate, existing):
            best_by_snapshot[candidate.snapshot_id] = candidate

    claim_summaries = build_claim_summaries(events, objective=objective, platform=platform)
    claims_by_snapshot: dict[str, list] = {}
    for claim in claim_summaries:
        claims_by_snapshot.setdefault(claim.candidate_snapshot_id, []).append(claim)

    members = []
    for candidate in best_by_snapshot.values():
        claims = claims_by_snapshot.get(candidate.snapshot_id, [])
        members.append(
            FrontierMember(
                snapshot_id=candidate.snapshot_id,
                workspace_id=candidate.workspace_id,
                run_id=candidate.run_id,
                objective=candidate.objective,
                platform=candidate.platform,
                budget_seconds=candidate.budget_seconds,
                metric_name=candidate.metric_name,
                metric_value=candidate.metric_value,
                direction=candidate.direction,
                claim_count=len(claims),
                support_count=sum(claim.support_count for claim in claims),
                contradiction_count=sum(claim.contradiction_count for claim in claims),
                tags=candidate.tags,
                last_updated_at=candidate.last_updated_at,
            )
        )

    members.sort(key=lambda item: _sort_key(item))
    return FrontierView(objective=objective, platform=platform, budget_seconds=budget_seconds, members=members[:limit])


def init_frontier_projection_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {FRONTIER_MEMBER_TABLE} (
            snapshot_id TEXT NOT NULL,
            objective TEXT NOT NULL,
            platform TEXT NOT NULL,
            budget_seconds INTEGER NOT NULL,
            workspace_id TEXT,
            run_id TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            direction TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            last_updated_at TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, objective, platform, budget_seconds)
        )
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{FRONTIER_MEMBER_TABLE}_lookup
        ON {FRONTIER_MEMBER_TABLE}(objective, platform, budget_seconds)
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {FRONTIER_CLAIM_TABLE} (
            claim_id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            objective TEXT NOT NULL,
            platform TEXT NOT NULL,
            support_count INTEGER NOT NULL DEFAULT 0,
            contradiction_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{FRONTIER_CLAIM_TABLE}_lookup
        ON {FRONTIER_CLAIM_TABLE}(snapshot_id, objective, platform)
        """
    )


def reset_frontier_projection(conn: sqlite3.Connection) -> None:
    conn.execute(f"DELETE FROM {FRONTIER_MEMBER_TABLE}")
    conn.execute(f"DELETE FROM {FRONTIER_CLAIM_TABLE}")


def apply_frontier_projection_event(conn: sqlite3.Connection, event: EventEnvelope) -> None:
    payload = event.payload

    if event.kind == EventKind.RUN_COMPLETED:
        if payload.get("status") != "success":
            return

        candidate = _RunCandidate(
            workspace_id=event.workspace_id,
            run_id=payload["run_id"],
            snapshot_id=payload["snapshot_id"],
            objective=payload["objective"],
            platform=payload["platform"],
            budget_seconds=int(payload["budget_seconds"]),
            metric_name=payload["metric_name"],
            metric_value=float(payload["metric_value"]),
            direction=payload["direction"],
            last_updated_at=event.occurred_at,
            tags=event.tags,
        )
        _upsert_frontier_member(conn, candidate)
        return

    if event.kind == EventKind.CLAIM_ASSERTED:
        conn.execute(
            f"""
            INSERT INTO {FRONTIER_CLAIM_TABLE} (
                claim_id, snapshot_id, objective, platform, support_count, contradiction_count
            ) VALUES (?, ?, ?, ?, 0, 0)
            ON CONFLICT(claim_id) DO UPDATE SET
                snapshot_id = excluded.snapshot_id,
                objective = excluded.objective,
                platform = excluded.platform,
                support_count = 0,
                contradiction_count = 0
            """,
            (
                payload["claim_id"],
                payload["candidate_snapshot_id"],
                payload["objective"],
                payload["platform"],
            ),
        )
        return

    if event.kind == EventKind.CLAIM_REPRODUCED:
        _increment_claim_counter(conn, claim_id=payload["claim_id"], column="support_count")
        return

    if event.kind == EventKind.CLAIM_CONTRADICTED:
        _increment_claim_counter(conn, claim_id=payload["claim_id"], column="contradiction_count")


def load_frontier_view(
    conn: sqlite3.Connection,
    *,
    objective: str,
    platform: str,
    budget_seconds: int | None = None,
    limit: int = 10,
) -> FrontierView:
    filters = ["member.objective = ?", "member.platform = ?"]
    params: list[str | int] = [objective, platform]

    if budget_seconds is not None:
        filters.append("member.budget_seconds = ?")
        params.append(budget_seconds)

    rows = conn.execute(
        f"""
        SELECT
            member.snapshot_id,
            member.workspace_id,
            member.run_id,
            member.objective,
            member.platform,
            member.budget_seconds,
            member.metric_name,
            member.metric_value,
            member.direction,
            member.tags_json,
            member.last_updated_at,
            COALESCE(claims.claim_count, 0) AS claim_count,
            COALESCE(claims.support_count, 0) AS support_count,
            COALESCE(claims.contradiction_count, 0) AS contradiction_count
        FROM {FRONTIER_MEMBER_TABLE} AS member
        LEFT JOIN (
            SELECT
                snapshot_id,
                objective,
                platform,
                COUNT(*) AS claim_count,
                COALESCE(SUM(support_count), 0) AS support_count,
                COALESCE(SUM(contradiction_count), 0) AS contradiction_count
            FROM {FRONTIER_CLAIM_TABLE}
            GROUP BY snapshot_id, objective, platform
        ) AS claims
            ON claims.snapshot_id = member.snapshot_id
           AND claims.objective = member.objective
           AND claims.platform = member.platform
        WHERE {' AND '.join(filters)}
        """,
        params,
    ).fetchall()

    members = [
        FrontierMember(
            snapshot_id=row["snapshot_id"],
            workspace_id=row["workspace_id"],
            run_id=row["run_id"],
            objective=row["objective"],
            platform=row["platform"],
            budget_seconds=row["budget_seconds"],
            metric_name=row["metric_name"],
            metric_value=row["metric_value"],
            direction=row["direction"],
            claim_count=row["claim_count"],
            support_count=row["support_count"],
            contradiction_count=row["contradiction_count"],
            tags=json.loads(row["tags_json"]),
            last_updated_at=row["last_updated_at"],
        )
        for row in rows
    ]
    members.sort(key=_sort_key)
    return FrontierView(objective=objective, platform=platform, budget_seconds=budget_seconds, members=members[:limit])


FRONTIER_PROJECTION = SQLiteProjection(
    name="frontier",
    schema_version=1,
    checksum_source="frontier_projection_members_v1|frontier_projection_claims_v1",
    init_schema=init_frontier_projection_schema,
    reset=reset_frontier_projection,
    apply=apply_frontier_projection_event,
)


def _is_better(candidate: _RunCandidate, existing: _RunCandidate) -> bool:
    if candidate.direction != existing.direction:
        return False
    if candidate.direction == "min":
        return candidate.metric_value < existing.metric_value
    return candidate.metric_value > existing.metric_value


def _sort_key(member: FrontierMember):
    if member.direction == "min":
        return (member.metric_value, member.snapshot_id)
    return (-member.metric_value, member.snapshot_id)


def _upsert_frontier_member(conn: sqlite3.Connection, candidate: _RunCandidate) -> None:
    existing_row = conn.execute(
        f"""
        SELECT *
        FROM {FRONTIER_MEMBER_TABLE}
        WHERE snapshot_id = ? AND objective = ? AND platform = ? AND budget_seconds = ?
        """,
        (
            candidate.snapshot_id,
            candidate.objective,
            candidate.platform,
            candidate.budget_seconds,
        ),
    ).fetchone()

    if existing_row is not None:
        existing = _RunCandidate(
            workspace_id=existing_row["workspace_id"],
            run_id=existing_row["run_id"],
            snapshot_id=existing_row["snapshot_id"],
            objective=existing_row["objective"],
            platform=existing_row["platform"],
            budget_seconds=existing_row["budget_seconds"],
            metric_name=existing_row["metric_name"],
            metric_value=existing_row["metric_value"],
            direction=existing_row["direction"],
            last_updated_at=existing_row["last_updated_at"],
            tags=json.loads(existing_row["tags_json"]),
        )
        if not _is_better(candidate, existing):
            return

    conn.execute(
        f"""
        INSERT INTO {FRONTIER_MEMBER_TABLE} (
            snapshot_id,
            objective,
            platform,
            budget_seconds,
            workspace_id,
            run_id,
            metric_name,
            metric_value,
            direction,
            tags_json,
            last_updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(snapshot_id, objective, platform, budget_seconds) DO UPDATE SET
            workspace_id = excluded.workspace_id,
            run_id = excluded.run_id,
            metric_name = excluded.metric_name,
            metric_value = excluded.metric_value,
            direction = excluded.direction,
            tags_json = excluded.tags_json,
            last_updated_at = excluded.last_updated_at
        """,
        (
            candidate.snapshot_id,
            candidate.objective,
            candidate.platform,
            candidate.budget_seconds,
            candidate.workspace_id,
            candidate.run_id,
            candidate.metric_name,
            candidate.metric_value,
            candidate.direction,
            json.dumps(candidate.tags, sort_keys=True),
            candidate.last_updated_at.isoformat(),
        ),
    )


def _increment_claim_counter(conn: sqlite3.Connection, *, claim_id: str, column: str) -> None:
    conn.execute(
        f"""
        UPDATE {FRONTIER_CLAIM_TABLE}
        SET {column} = {column} + 1
        WHERE claim_id = ?
        """,
        (claim_id,),
    )
