from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import create_app
from research_os.artifacts.local import LocalArtifactRegistry
from research_os.settings import Settings


def test_create_workspace_and_publish_run(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "test.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"demo snapshot artifact")

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "tags": {"topic": "demo"},
        },
    )
    assert create_response.status_code == 201
    workspace_id = create_response.json()["workspace_id"]

    snapshot_response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-demo-1",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-demo-1",
                "parent_snapshot_ids": ["snap-baseline"],
                "artifact_uri": snapshot_artifact.uri,
            },
            "tags": {"topic": "demo"},
        },
    )
    assert snapshot_response.status_code == 201

    run_response = client.post(
        "/api/v1/events",
        json={
            "kind": "run.completed",
            "workspace_id": workspace_id,
            "aggregate_id": "run-demo-1",
            "aggregate_kind": "run",
            "payload": {
                "run_id": "run-demo-1",
                "snapshot_id": "snap-demo-1",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.23,
                "direction": "min",
                "status": "success",
            },
            "tags": {"topic": "demo"},
        },
    )
    assert run_response.status_code == 201

    frontier_response = client.get("/api/v1/frontiers/val_bpb/A100?budget_seconds=300")
    assert frontier_response.status_code == 200
    members = frontier_response.json()["members"]
    assert len(members) == 1
    assert members[0]["snapshot_id"] == "snap-demo-1"

    workspace_response = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert workspace_response.status_code == 200
    body = workspace_response.json()
    assert body["run_ids"] == ["run-demo-1"]
    assert body["snapshot_ids"] == ["snap-demo-1"]

    events_response = client.get(
        f"/api/v1/events?workspace_id={workspace_id}&kind=snapshot.published"
    )
    assert events_response.status_code == 200
    snapshot_event = events_response.json()[0]
    assert snapshot_event["payload"]["artifact_uri"] == snapshot_artifact.uri
    assert artifact_registry.read_bytes(snapshot_artifact.uri) == b"demo snapshot artifact"


def test_snapshot_event_round_trips_git_ref_and_bundle_digest(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "snapshot.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"bundle for snapshot metadata test")

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "snapshot-meta-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    assert create_response.status_code == 201
    workspace_id = create_response.json()["workspace_id"]

    snapshot_response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-demo-meta-1",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-demo-meta-1",
                "parent_snapshot_ids": ["snap-baseline"],
                "artifact_uri": snapshot_artifact.uri,
                "source_bundle_digest": snapshot_artifact.digest,
                "git_ref": "refs/workspaces/snapshot-meta-demo",
            },
        },
    )
    assert snapshot_response.status_code == 201

    events_response = client.get(
        f"/api/v1/events?workspace_id={workspace_id}&kind=snapshot.published"
    )
    assert events_response.status_code == 200
    snapshot_event = events_response.json()[0]
    assert snapshot_event["payload"]["artifact_uri"] == snapshot_artifact.uri
    assert snapshot_event["payload"]["source_bundle_digest"] == snapshot_artifact.digest
    assert snapshot_event["payload"]["git_ref"] == "refs/workspaces/snapshot-meta-demo"


def test_claim_summary_api_uses_materialized_claim_projection(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "claims.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "claims-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "claim.asserted",
                "workspace_id": workspace_id,
                "aggregate_id": "claim-1",
                "aggregate_kind": "claim",
                "payload": {
                    "claim_id": "claim-1",
                    "statement": "Optimizer helps",
                    "claim_type": "improvement",
                    "candidate_snapshot_id": "snap-1",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "evidence_run_ids": ["run-1"],
                },
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "claim.reproduced",
                "workspace_id": workspace_id,
                "aggregate_id": "claim-1",
                "aggregate_kind": "claim",
                "payload": {"claim_id": "claim-1", "evidence_run_id": "run-2"},
            },
        ).status_code
        == 201
    )

    claims_response = client.get("/api/v1/claims?objective=val_bpb&platform=A100")
    assert claims_response.status_code == 200
    claims = claims_response.json()
    assert len(claims) == 1
    assert claims[0]["claim_id"] == "claim-1"
    assert claims[0]["support_count"] == 1
    assert claims[0]["status"] == "supported"
