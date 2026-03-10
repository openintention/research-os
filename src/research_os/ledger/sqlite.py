from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from research_os.domain.models import ClaimSummary, EventEnvelope, EventKind, FrontierView
from research_os.projections.claims import CLAIMS_PROJECTION, load_claim_summaries
from research_os.projections.frontier import FRONTIER_PROJECTION, load_frontier_view
from research_os.projections.materialized import init_projection_metadata_schema


class SQLiteEventStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._projections = (FRONTIER_PROJECTION, CLAIMS_PROJECTION)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    workspace_id TEXT,
                    aggregate_id TEXT,
                    aggregate_kind TEXT,
                    actor_id TEXT,
                    payload_json TEXT NOT NULL,
                    tags_json TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_workspace ON events(workspace_id, occurred_at)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind, occurred_at)")
            init_projection_metadata_schema(conn)
            for projection in self._projections:
                projection.init_schema(conn)
            self._refresh_outdated_projections(conn)

    def append(self, event: EventEnvelope) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO events (
                    event_id, kind, occurred_at, workspace_id, aggregate_id, aggregate_kind,
                    actor_id, payload_json, tags_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    event.event_id,
                    event.kind.value,
                    event.occurred_at.isoformat(),
                    event.workspace_id,
                    event.aggregate_id,
                    event.aggregate_kind,
                    event.actor_id,
                    json.dumps(event.payload, sort_keys=True),
                    json.dumps(event.tags, sort_keys=True),
                ),
            )
            for projection in self._projections:
                projection.apply(conn, event)

    def list(
        self,
        *,
        workspace_id: str | None = None,
        kind: EventKind | None = None,
        limit: int | None = None,
    ) -> list[EventEnvelope]:
        with self._connect() as conn:
            return self._list_with_connection(
                conn,
                workspace_id=workspace_id,
                kind=kind,
                limit=limit,
            )

    def get_frontier(
        self,
        *,
        objective: str,
        platform: str,
        budget_seconds: int | None = None,
        limit: int = 10,
    ) -> FrontierView:
        with self._connect() as conn:
            return load_frontier_view(
                conn,
                objective=objective,
                platform=platform,
                budget_seconds=budget_seconds,
                limit=limit,
            )

    def rebuild_frontier_projection(self) -> None:
        with self._connect() as conn:
            FRONTIER_PROJECTION.rebuild(conn, self._list_with_connection(conn))

    def list_claims(
        self,
        *,
        objective: str | None = None,
        platform: str | None = None,
    ) -> list[ClaimSummary]:
        with self._connect() as conn:
            return load_claim_summaries(conn, objective=objective, platform=platform)

    def rebuild_claim_projection(self) -> None:
        with self._connect() as conn:
            CLAIMS_PROJECTION.rebuild(conn, self._list_with_connection(conn))

    def _refresh_outdated_projections(self, conn: sqlite3.Connection) -> None:
        events: list[EventEnvelope] | None = None
        for projection in self._projections:
            if projection.is_current(conn):
                continue
            if events is None:
                events = self._list_with_connection(conn)
            projection.rebuild(conn, events)

    def _list_with_connection(
        self,
        conn: sqlite3.Connection,
        *,
        workspace_id: str | None = None,
        kind: EventKind | None = None,
        limit: int | None = None,
    ) -> list[EventEnvelope]:
        clauses: list[str] = []
        params: list[str | int] = []

        if workspace_id:
            clauses.append("workspace_id = ?")
            params.append(workspace_id)
        if kind:
            clauses.append("kind = ?")
            params.append(kind.value)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_sql = "LIMIT ?" if limit else ""
        if limit:
            params.append(limit)

        query = f'''
            SELECT * FROM events
            {where}
            ORDER BY occurred_at ASC, event_id ASC
            {limit_sql}
        '''
        rows = conn.execute(query, params).fetchall()
        return [
            EventEnvelope(
                event_id=row["event_id"],
                kind=EventKind(row["kind"]),
                occurred_at=row["occurred_at"],
                workspace_id=row["workspace_id"],
                aggregate_id=row["aggregate_id"],
                aggregate_kind=row["aggregate_kind"],
                actor_id=row["actor_id"],
                payload=json.loads(row["payload_json"]),
                tags=json.loads(row["tags_json"]),
            )
            for row in rows
        ]
