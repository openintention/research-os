from __future__ import annotations

import sqlite3

from research_os.domain.models import EventEnvelope, EventKind
from research_os.ledger.sqlite import SQLiteEventStore
from research_os.projections.claims import build_claim_summaries
from research_os.projections.frontier import build_frontier
from research_os.projections.claims import CLAIMS_PROJECTION
from research_os.projections.frontier import FRONTIER_PROJECTION
from research_os.projections.materialized import PROJECTION_METADATA_TABLE
from research_os.service import ResearchOSService


def _start_workspace(
    service: ResearchOSService,
    *,
    workspace_id: str,
    objective: str,
    platform: str = "A100",
    budget_seconds: int = 300,
) -> None:
    service.append_event(
        EventEnvelope(
            kind=EventKind.WORKSPACE_STARTED,
            workspace_id=workspace_id,
            aggregate_id=workspace_id,
            aggregate_kind="workspace",
            payload={
                "name": workspace_id,
                "objective": objective,
                "platform": platform,
                "budget_seconds": budget_seconds,
            },
        )
    )


def _start_run(
    service: ResearchOSService,
    *,
    workspace_id: str,
    run_id: str,
    snapshot_id: str,
    objective: str,
    platform: str = "A100",
    budget_seconds: int = 300,
) -> None:
    workspace = service.get_workspace(workspace_id)
    assert workspace is not None
    if snapshot_id not in workspace.snapshot_ids:
        service.append_event(
            EventEnvelope(
                kind=EventKind.SNAPSHOT_PUBLISHED,
                workspace_id=workspace_id,
                aggregate_id=snapshot_id,
                aggregate_kind="snapshot",
                payload={
                    "snapshot_id": snapshot_id,
                    "artifact_uri": "artifact://sha256/" + "a" * 64,
                },
            )
        )
    service.append_event(
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id=workspace_id,
            aggregate_id=run_id,
            aggregate_kind="run",
            payload={
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "objective": objective,
                "platform": platform,
                "budget_seconds": budget_seconds,
                "metric_name": objective,
                "metric_value": 1.2,
                "direction": "min",
                "status": "success",
            },
        )
    )


def test_frontier_uses_best_snapshot_run():
    events = [
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id="ws",
            payload={
                "run_id": "run-1",
                "snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.28,
                "direction": "min",
                "status": "success",
            },
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id="ws",
            payload={
                "run_id": "run-2",
                "snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.22,
                "direction": "min",
                "status": "success",
            },
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id="ws",
            payload={
                "run_id": "run-3",
                "snapshot_id": "snap-2",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.25,
                "direction": "min",
                "status": "success",
            },
        ),
    ]

    frontier = build_frontier(events, objective="val_bpb", platform="A100", budget_seconds=300)
    assert frontier.members[0].run_id == "run-2"
    assert frontier.members[0].snapshot_id == "snap-1"


def test_claim_summary_support_and_contradiction():
    events = [
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id="ws",
            payload={
                "claim_id": "claim-1",
                "statement": "Something improves",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
            },
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_REPRODUCED,
            workspace_id="ws",
            payload={"claim_id": "claim-1", "evidence_run_id": "run-1"},
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_CONTRADICTED,
            workspace_id="ws",
            payload={"claim_id": "claim-1", "evidence_run_id": "run-2"},
        ),
    ]

    claims = build_claim_summaries(events)
    assert claims[0].support_count == 1
    assert claims[0].contradiction_count == 1
    assert claims[0].status == "contested"


def test_materialized_frontier_matches_full_scan_without_listing_events(tmp_path, monkeypatch):
    store = SQLiteEventStore(str(tmp_path / "frontier.db"))
    service = ResearchOSService(store)
    _start_workspace(service, workspace_id="ws-1", objective="val_bpb")
    _start_workspace(service, workspace_id="ws-2", objective="val_bpb")

    events = [
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id="ws-1",
            aggregate_id="run-1",
            aggregate_kind="run",
            payload={
                "run_id": "run-1",
                "snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.24,
                "direction": "min",
                "status": "success",
            },
            tags={"topic": "attention"},
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id="ws-2",
            aggregate_id="run-2",
            aggregate_kind="run",
            payload={
                "run_id": "run-2",
                "snapshot_id": "snap-2",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.21,
                "direction": "min",
                "status": "success",
            },
            tags={"topic": "optimizer"},
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id="ws-2",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-1",
                "statement": "Optimizer helps",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-2",
                "objective": "val_bpb",
                "platform": "A100",
            },
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_REPRODUCED,
            workspace_id="ws-2",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={"claim_id": "claim-1", "evidence_run_id": "run-2"},
        ),
    ]

    _start_run(
        service,
        workspace_id="ws-1",
        run_id="run-1",
        snapshot_id="snap-1",
        objective="val_bpb",
    )
    _start_run(
        service,
        workspace_id="ws-2",
        run_id="run-2",
        snapshot_id="snap-2",
        objective="val_bpb",
    )

    for event in events:
        service.append_event(event)

    expected = build_frontier(
        store.list(limit=10_000),
        objective="val_bpb",
        platform="A100",
        budget_seconds=300,
    ).model_dump(mode="json")

    def fail_list(*args, **kwargs):
        raise AssertionError("frontier query should use the materialized projection")

    monkeypatch.setattr(store, "list", fail_list)

    frontier = service.get_frontier(objective="val_bpb", platform="A100", budget_seconds=300)
    assert frontier.model_dump(mode="json") == expected


def test_frontier_projection_rebuild_restores_materialized_state(tmp_path):
    db_path = tmp_path / "frontier-rebuild.db"
    store = SQLiteEventStore(str(db_path))
    service = ResearchOSService(store)
    _start_workspace(service, workspace_id="ws-1", objective="val_bpb")
    _start_run(
        service,
        workspace_id="ws-1",
        run_id="run-3",
        snapshot_id="snap-1",
        objective="val_bpb",
    )

    events = [
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id="ws-1",
            aggregate_id="run-1",
            aggregate_kind="run",
            payload={
                "run_id": "run-1",
                "snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.26,
                "direction": "min",
                "status": "success",
            },
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id="ws-1",
            aggregate_id="run-2",
            aggregate_kind="run",
            payload={
                "run_id": "run-2",
                "snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.19,
                "direction": "min",
                "status": "success",
            },
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id="ws-1",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-1",
                "statement": "Improves frontier",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
            },
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_CONTRADICTED,
            workspace_id="ws-1",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={"claim_id": "claim-1", "evidence_run_id": "run-3"},
        ),
    ]

    for event in events:
        service.append_event(event)

    expected = build_frontier(
        store.list(limit=10_000),
        objective="val_bpb",
        platform="A100",
        budget_seconds=300,
    ).model_dump(mode="json")

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM frontier_projection_members")
        conn.execute("DELETE FROM frontier_projection_claims")

    assert service.get_frontier(objective="val_bpb", platform="A100", budget_seconds=300).members == []

    service.rebuild_frontier_projection()

    rebuilt = service.get_frontier(objective="val_bpb", platform="A100", budget_seconds=300)
    assert rebuilt.model_dump(mode="json") == expected


def test_materialized_claims_match_full_scan_without_listing_events(tmp_path, monkeypatch):
    store = SQLiteEventStore(str(tmp_path / "claims.db"))
    service = ResearchOSService(store)
    _start_workspace(service, workspace_id="ws-1", objective="val_bpb")
    _start_workspace(service, workspace_id="ws-2", objective="val_bpb")
    _start_workspace(service, workspace_id="ws-3", objective="val_bpb")
    _start_run(
        service,
        workspace_id="ws-1",
        run_id="run-1",
        snapshot_id="snap-1",
        objective="val_bpb",
    )
    _start_run(
        service,
        workspace_id="ws-2",
        run_id="run-2",
        snapshot_id="snap-2",
        objective="val_bpb",
    )
    _start_run(
        service,
        workspace_id="ws-3",
        run_id="run-3",
        snapshot_id="snap-3",
        objective="val_bpb",
    )

    events = [
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id="ws-1",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-1",
                "statement": "Attention helps",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
                "metric_name": "val_bpb",
                "delta": -0.02,
                "evidence_run_ids": ["run-1"],
            },
            tags={"topic": "attention"},
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_REPRODUCED,
            workspace_id="ws-2",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={"claim_id": "claim-1", "evidence_run_id": "run-2"},
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_CONTRADICTED,
            workspace_id="ws-3",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={"claim_id": "claim-1", "evidence_run_id": "run-3"},
        ),
    ]

    for event in events:
        service.append_event(event)

    expected = build_claim_summaries(
        store.list(limit=10_000),
        objective="val_bpb",
        platform="A100",
    )

    def fail_list(*args, **kwargs):
        raise AssertionError("claim query should use the materialized projection")

    monkeypatch.setattr(store, "list", fail_list)

    claims = service.list_claims(objective="val_bpb", platform="A100")
    assert [claim.model_dump(mode="json") for claim in claims] == [
        claim.model_dump(mode="json") for claim in expected
    ]


def test_claim_projection_rebuild_restores_materialized_state(tmp_path):
    db_path = tmp_path / "claim-rebuild.db"
    store = SQLiteEventStore(str(db_path))
    service = ResearchOSService(store)
    _start_workspace(service, workspace_id="ws-1", objective="val_bpb")
    _start_workspace(service, workspace_id="ws-2", objective="val_bpb")
    service.append_event(
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id="ws-1",
            aggregate_id="snap-1",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-1",
                "artifact_uri": "artifact://sha256/" + "a" * 64,
            },
        )
    )
    _start_run(
        service,
        workspace_id="ws-2",
        run_id="run-1",
        snapshot_id="snap-2",
        objective="val_bpb",
    )

    events = [
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id="ws-1",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-1",
                "statement": "Improves perplexity",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
                "confidence": 0.7,
            },
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_REPRODUCED,
            workspace_id="ws-2",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={"claim_id": "claim-1", "evidence_run_id": "run-1"},
        ),
    ]

    for event in events:
        service.append_event(event)

    expected = build_claim_summaries(store.list(limit=10_000))

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM claim_projection_summaries")

    assert service.list_claims() == []

    service.rebuild_claim_projection()

    rebuilt = service.list_claims()
    assert [claim.model_dump(mode="json") for claim in rebuilt] == [
        claim.model_dump(mode="json") for claim in expected
    ]


def test_projection_metadata_rebuilds_outdated_frontier_and_claim_state(tmp_path):
    db_path = tmp_path / "projection-metadata.db"
    store = SQLiteEventStore(str(db_path))
    service = ResearchOSService(store)
    _start_workspace(service, workspace_id="ws-1", objective="val_bpb")
    _start_workspace(service, workspace_id="ws-2", objective="val_bpb")
    service.append_event(
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id="ws-1",
            aggregate_id="snap-1",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-1",
                "artifact_uri": "artifact://sha256/" + "a" * 64,
            },
        )
    )
    _start_run(
        service,
        workspace_id="ws-2",
        run_id="run-2",
        snapshot_id="snap-2",
        objective="val_bpb",
    )

    events = [
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id="ws-1",
            aggregate_id="run-1",
            aggregate_kind="run",
            payload={
                "run_id": "run-1",
                "snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.18,
                "direction": "min",
                "status": "success",
            },
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id="ws-1",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-1",
                "statement": "Improves the frontier",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-1",
                "objective": "val_bpb",
                "platform": "A100",
            },
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_REPRODUCED,
            workspace_id="ws-2",
            aggregate_id="claim-1",
            aggregate_kind="claim",
            payload={"claim_id": "claim-1", "evidence_run_id": "run-2"},
        ),
    ]

    for event in events:
        service.append_event(event)

    expected_frontier = build_frontier(
        store.list(limit=10_000),
        objective="val_bpb",
        platform="A100",
        budget_seconds=300,
    ).model_dump(mode="json")
    expected_claims = build_claim_summaries(store.list(limit=10_000))

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE projection_metadata SET schema_version = 0, checksum = 'stale'")
        conn.execute("DELETE FROM frontier_projection_members")
        conn.execute("DELETE FROM frontier_projection_claims")
        conn.execute("DELETE FROM claim_projection_summaries")

    reloaded = ResearchOSService(SQLiteEventStore(str(db_path)))

    frontier = reloaded.get_frontier(objective="val_bpb", platform="A100", budget_seconds=300)
    assert frontier.model_dump(mode="json") == expected_frontier

    claims = reloaded.list_claims()
    assert [claim.model_dump(mode="json") for claim in claims] == [
        claim.model_dump(mode="json") for claim in expected_claims
    ]

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT projection_name, schema_version, checksum
            FROM {PROJECTION_METADATA_TABLE}
            ORDER BY projection_name
            """
        ).fetchall()

    assert rows == [
        ("claims", CLAIMS_PROJECTION.schema_version, CLAIMS_PROJECTION.checksum),
        ("frontier", FRONTIER_PROJECTION.schema_version, FRONTIER_PROJECTION.checksum),
    ]
