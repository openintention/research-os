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
    assert body["participant_role"] == "contributor"
    assert body["run_ids"] == ["run-demo-1"]
    assert body["snapshot_ids"] == ["snap-demo-1"]

    events_response = client.get(
        f"/api/v1/events?workspace_id={workspace_id}&kind=snapshot.published"
    )
    assert events_response.status_code == 200
    snapshot_event = events_response.json()[0]
    assert snapshot_event["payload"]["artifact_uri"] == snapshot_artifact.uri
    assert artifact_registry.read_bytes(snapshot_artifact.uri) == b"demo snapshot artifact"


def test_workspace_api_round_trips_explicit_participant_role(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "role.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "verifier-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "actor_id": "verifier-1",
            "participant_role": "verifier",
        },
    )
    assert create_response.status_code == 201
    workspace_id = create_response.json()["workspace_id"]

    workspace_response = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert workspace_response.status_code == 200
    workspace = workspace_response.json()
    assert workspace["actor_id"] == "verifier-1"
    assert workspace["participant_role"] == "verifier"

    events_response = client.get(f"/api/v1/events?workspace_id={workspace_id}&kind=workspace.started")
    assert events_response.status_code == 200
    started_event = events_response.json()[0]
    assert started_event["payload"]["participant_role"] == "verifier"
    assert started_event["tags"]["participant_role"] == "verifier"


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
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-1",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-1",
                    "artifact_uri": "artifact://sha256/" + "a" * 64,
                },
                "tags": {"topic": "claim-demo"},
            },
        ).status_code
        == 201
    )

    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "run.completed",
                "workspace_id": workspace_id,
                "aggregate_id": "run-1",
                "aggregate_kind": "run",
                "payload": {
                    "run_id": "run-1",
                    "snapshot_id": "snap-1",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                    "metric_name": "val_bpb",
                    "metric_value": 1.21,
                    "direction": "min",
                    "status": "success",
                },
                "tags": {"topic": "claim-demo"},
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "run.completed",
                "workspace_id": workspace_id,
                "aggregate_id": "run-2",
                "aggregate_kind": "run",
                "payload": {
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
                "tags": {"topic": "claim-demo"},
            },
        ).status_code
        == 201
    )

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


def test_append_event_rejects_invalid_ingestion_payload(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "invalid-ingest.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "bad-events",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    assert create_response.status_code == 201
    workspace_id = create_response.json()["workspace_id"]

    bad_payload_response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-bad",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-bad",
                "artifact_uri": "ftp://invalid.example.com/artifact.bin",
            },
        },
    )
    assert bad_payload_response.status_code == 400
    assert bad_payload_response.json()["detail"] == (
        "artifact_uri must use artifact, http, https, or file scheme"
    )


def test_append_snapshot_event_rejects_mismatched_manifest_digest(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "snapshot-mismatch.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "mismatch-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    mismatch_response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-mismatch",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-mismatch",
                "artifact_uri": f"artifact://sha256/{'a' * 64}",
                "source_bundle_digest": "sha256:" + "b" * 64,
                "source_bundle_manifest_uri": f"artifact://sha256/{'c' * 64}",
                "source_bundle_manifest_digest": "sha256:" + "b" * 64,
                "source_bundle_manifest_signature": "sig-123",
            },
        },
    )
    assert mismatch_response.status_code == 400
    assert mismatch_response.json()["detail"] == (
        "source_bundle_manifest_digest must match digest in source_bundle_manifest_uri"
    )


def test_append_snapshot_event_rejects_invalid_source_bundle_digest_format(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "snapshot-bad-digest.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "snapshot-bad-digest-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    invalid_digest_response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-bad-digest",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-bad-digest",
                "artifact_uri": "file:///tmp/local-artifact-bundle.json",
                "source_bundle_digest": "not-a-valid-digest",
            },
        },
    )
    assert invalid_digest_response.status_code == 400
    assert invalid_digest_response.json()["detail"] == "source_bundle_digest must be a sha256 digest"


def test_append_snapshot_event_rejects_manifest_signature_without_digest(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "snapshot-signature-without-digest.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "snapshot-signature-without-digest-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    signature_without_digest_response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-signature-no-digest",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-signature-no-digest",
                "artifact_uri": "file:///tmp/local-artifact-bundle.json",
                "source_bundle_manifest_uri": "artifact://sha256/" + "a" * 64,
                "source_bundle_manifest_signature": "sig-123",
            },
        },
    )
    assert signature_without_digest_response.status_code == 400
    assert (
        signature_without_digest_response.json()["detail"]
        == "source_bundle_manifest_signature requires source_bundle_manifest_digest for validation context"
    )


def test_append_snapshot_event_validates_source_bundle_digest_when_artifact_uri_is_digest(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "snapshot-aligned.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "aligned-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    aligned_response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-aligned",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-aligned",
                "artifact_uri": f"artifact://sha256/{'a' * 64}",
                "source_bundle_digest": "sha256:" + "a" * 64,
                "source_bundle_manifest_uri": f"artifact://sha256/{'c' * 64}",
                "source_bundle_manifest_digest": "sha256:" + "c" * 64,
                "source_bundle_manifest_signature": "sig-123",
            },
        },
    )
    assert aligned_response.status_code == 201


def test_append_snapshot_event_accepts_manifest_provenance_metadata_version_fields(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "snapshot-provenance-versioning.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "snapshot-provenance-version-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-versioned",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-versioned",
                "artifact_uri": "artifact://sha256/" + "a" * 64,
                "source_bundle_manifest_uri": "artifact://sha256/" + "c" * 64,
                "source_bundle_manifest_digest": "sha256:" + "c" * 64,
                "source_bundle_manifest_signature": "sig-123",
                "source_bundle_manifest_signature_scheme": "ed25519",
                "source_bundle_manifest_provenance_schema": "openintention-artifact-manifest-v1",
                "source_bundle_manifest_provenance_version": "1",
            },
        },
    )
    assert response.status_code == 201


def test_append_snapshot_event_rejects_manifest_provenance_version_without_schema(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "snapshot-provenance-version-no-schema.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "snapshot-provenance-no-schema",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-version-no-schema",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-version-no-schema",
                "artifact_uri": "artifact://sha256/" + "a" * 64,
                "source_bundle_manifest_uri": "artifact://sha256/" + "c" * 64,
                "source_bundle_manifest_digest": "sha256:" + "c" * 64,
                "source_bundle_manifest_signature": "sig-123",
                "source_bundle_manifest_provenance_version": "1",
            },
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "source_bundle_manifest_provenance_schema is required when source_bundle_manifest_provenance_version is provided"
    )


def test_append_snapshot_event_rejects_invalid_manifest_provenance_version(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "snapshot-provenance-bad-version.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "snapshot-provenance-bad-version",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-bad-version",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-bad-version",
                "artifact_uri": "artifact://sha256/" + "a" * 64,
                "source_bundle_manifest_uri": "artifact://sha256/" + "c" * 64,
                "source_bundle_manifest_digest": "sha256:" + "c" * 64,
                "source_bundle_manifest_signature": "sig-123",
                "source_bundle_manifest_signature_scheme": "ed25519",
                "source_bundle_manifest_provenance_schema": "openintention-artifact-manifest-v1",
                "source_bundle_manifest_provenance_version": "v1",
            },
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "source_bundle_manifest_provenance_version must be an integer version string"


def test_append_snapshot_event_rejects_versioned_signature_without_signature_scheme(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "snapshot-provenance-no-scheme.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "snapshot-provenance-no-scheme",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-no-scheme",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-no-scheme",
                "artifact_uri": "artifact://sha256/" + "a" * 64,
                "source_bundle_manifest_uri": "artifact://sha256/" + "c" * 64,
                "source_bundle_manifest_digest": "sha256:" + "c" * 64,
                "source_bundle_manifest_signature": "sig-123",
                "source_bundle_manifest_provenance_schema": "openintention-artifact-manifest-v1",
                "source_bundle_manifest_provenance_version": "1",
            },
        },
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "source_bundle_manifest_signature_scheme is required when source_bundle_manifest_signature is provided"
    )


def test_append_claim_event_accepts_candidate_manifest_provenance_metadata_version_fields(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "claim-provenance-version.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "claim-provenance-version-demo",
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
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-provenance-version-source",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-provenance-version-source",
                    "artifact_uri": "file:///tmp/local-artifact-bundle.json",
                    "source_bundle_manifest_uri": "artifact://sha256/" + "a" * 64,
                    "source_bundle_manifest_digest": "sha256:" + "a" * 64,
                },
            },
        ).status_code
        == 201
    )

    response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.asserted",
            "workspace_id": workspace_id,
            "aggregate_id": "claim-provenance-version",
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": "claim-provenance-version",
                "statement": "Versioned provenance claim payload",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-provenance-version-source",
                "objective": "val_bpb",
                "platform": "A100",
                "candidate_snapshot_manifest_uri": "artifact://sha256/" + "a" * 64,
                "candidate_snapshot_manifest_digest": "sha256:" + "a" * 64,
                "candidate_snapshot_manifest_signature": "sig-456",
                "candidate_snapshot_manifest_signature_scheme": "ed25519",
                "candidate_snapshot_manifest_provenance_schema": "openintention-artifact-manifest-v1",
                "candidate_snapshot_manifest_provenance_version": "1",
            },
        },
    )
    assert response.status_code == 201


def test_append_claim_event_rejects_mismatched_candidate_manifest(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "claim-provenance.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "claim-manifest-mismatch-demo",
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
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-source",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-source",
                    "artifact_uri": "file:///tmp/local-artifact-bundle.json",
                    "source_bundle_manifest_uri": "artifact://sha256/" + "a" * 64,
                    "source_bundle_manifest_digest": "sha256:" + "a" * 64,
                },
            },
        ).status_code
        == 201
    )

    mismatch_claim_response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.asserted",
            "workspace_id": workspace_id,
            "aggregate_id": "claim-mismatch",
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": "claim-mismatch",
                "statement": "Mismatch candidate snapshot manifest",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-source",
                "objective": "val_bpb",
                "platform": "A100",
                "candidate_snapshot_manifest_uri": "artifact://sha256/" + "b" * 64,
                "candidate_snapshot_manifest_digest": "sha256:" + "b" * 64,
            },
        },
    )
    assert mismatch_claim_response.status_code == 400
    assert mismatch_claim_response.json()["detail"] == (
        "claim.asserted candidate snapshot manifest uri does not match source snapshot provenance"
    )


def test_append_claim_event_rejects_signature_without_candidate_manifest_digest(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "claim-signature-no-digest.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "claim-signature-no-digest-demo",
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
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-source-2",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-source-2",
                    "artifact_uri": "file:///tmp/local-artifact-bundle.json",
                    "source_bundle_manifest_uri": "artifact://sha256/" + "a" * 64,
                    "source_bundle_manifest_digest": "sha256:" + "a" * 64,
                },
            },
        ).status_code
        == 201
    )

    signature_without_digest_claim_response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.asserted",
            "workspace_id": workspace_id,
            "aggregate_id": "claim-signature-no-digest",
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": "claim-signature-no-digest",
                "statement": "Claim has signature without manifest digest",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-source-2",
                "objective": "val_bpb",
                "platform": "A100",
                "candidate_snapshot_manifest_uri": "artifact://sha256/" + "a" * 64,
                "candidate_snapshot_manifest_signature": "sig-456",
            },
        },
    )
    assert signature_without_digest_claim_response.status_code == 400
    assert (
        signature_without_digest_claim_response.json()["detail"]
        == "candidate_snapshot_manifest_signature requires candidate_snapshot_manifest_digest for validation context"
    )


def test_append_claim_event_rejects_invalid_candidate_manifest_digest_format(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "claim-bad-manifest-digest.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "claim-bad-manifest-digest-demo",
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
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-source-3",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-source-3",
                    "artifact_uri": "file:///tmp/local-artifact-bundle.json",
                },
            },
        ).status_code
        == 201
    )

    invalid_manifest_claim_response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.asserted",
            "workspace_id": workspace_id,
            "aggregate_id": "claim-bad-manifest-digest",
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": "claim-bad-manifest-digest",
                "statement": "Bad claim manifest digest",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-source-3",
                "objective": "val_bpb",
                "platform": "A100",
                "candidate_snapshot_manifest_uri": "artifact://sha256/" + "a" * 64,
                "candidate_snapshot_manifest_digest": "sha256:not-a-valid-digest",
            },
        },
    )
    assert invalid_manifest_claim_response.status_code == 400
    assert invalid_manifest_claim_response.json()["detail"] == "candidate_snapshot_manifest_digest must be a sha256 digest"


def test_append_event_rejects_duplicate_id_and_unknown_workspace(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "event-conflict.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "dup-events",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    assert create_response.status_code == 201
    workspace_id = create_response.json()["workspace_id"]

    fixed_event = {
        "kind": "snapshot.published",
        "workspace_id": workspace_id,
        "aggregate_id": "snap-dedup-1",
        "aggregate_kind": "snapshot",
        "event_id": "event-dedup",
        "payload": {
            "snapshot_id": "snap-dedup-1",
            "artifact_uri": "artifact://sha256/" + "a" * 64,
        },
    }

    first_response = client.post("/api/v1/events", json=fixed_event)
    assert first_response.status_code == 201
    duplicate_response = client.post("/api/v1/events", json=fixed_event)
    assert duplicate_response.status_code == 409

    unknown_workspace = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": "does-not-exist",
            "aggregate_id": "snap-ghost",
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": "snap-ghost",
                "artifact_uri": "artifact://sha256/" + "b" * 64,
            },
        },
    )
    assert unknown_workspace.status_code == 400


def test_create_workspace_rejects_unknown_effort_and_invalid_actor_id(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "workspace-validation.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    unknown_effort_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "bad-effort-workspace",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "effort_id": "effort-does-not-exist",
        },
    )
    assert unknown_effort_response.status_code == 400
    assert unknown_effort_response.json()["detail"] == (
        "workspace.started effort_id must reference a known effort"
    )

    invalid_actor_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "bad-actor-workspace",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "actor_id": "bad actor",
        },
    )
    assert invalid_actor_response.status_code == 400
    assert invalid_actor_response.json()["detail"] == "actor_id has invalid characters"


def test_append_run_event_rejects_unknown_workspace_snapshot(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "run-missing-snapshot.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "run-missing-snapshot-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    response = client.post(
        "/api/v1/events",
        json={
            "kind": "run.completed",
            "workspace_id": workspace_id,
            "aggregate_id": "run-missing-snapshot",
            "aggregate_kind": "run",
            "payload": {
                "run_id": "run-missing-snapshot",
                "snapshot_id": "snap-does-not-exist",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.23,
                "direction": "min",
                "status": "success",
            },
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "run.completed snapshot_id must reference a known workspace snapshot"
    )


def test_append_claim_event_rejects_unknown_candidate_snapshot_and_evidence_run(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "claim-reference-validation.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "claim-reference-validation",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    workspace_id = create_response.json()["workspace_id"]

    missing_snapshot_response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.asserted",
            "workspace_id": workspace_id,
            "aggregate_id": "claim-missing-snapshot",
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": "claim-missing-snapshot",
                "statement": "This should fail",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-missing",
                "objective": "val_bpb",
                "platform": "A100",
            },
        },
    )
    assert missing_snapshot_response.status_code == 400
    assert missing_snapshot_response.json()["detail"] == (
        "claim.asserted candidate_snapshot_id must reference a known workspace snapshot"
    )

    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-known",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-known",
                    "artifact_uri": "artifact://sha256/" + "a" * 64,
                },
            },
        ).status_code
        == 201
    )

    missing_run_response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.asserted",
            "workspace_id": workspace_id,
            "aggregate_id": "claim-missing-run",
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": "claim-missing-run",
                "statement": "This should also fail",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-known",
                "objective": "val_bpb",
                "platform": "A100",
                "evidence_run_ids": ["run-missing"],
            },
        },
    )
    assert missing_run_response.status_code == 400
    assert missing_run_response.json()["detail"] == (
        "claim.asserted evidence_run_ids must reference known workspace runs"
    )


def test_append_claim_feedback_rejects_unknown_workspace_run(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "claim-feedback-run-validation.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "claim-feedback-run-validation",
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
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-feedback",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-feedback",
                    "artifact_uri": "artifact://sha256/" + "a" * 64,
                },
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "run.completed",
                "workspace_id": workspace_id,
                "aggregate_id": "run-feedback",
                "aggregate_kind": "run",
                "payload": {
                    "run_id": "run-feedback",
                    "snapshot_id": "snap-feedback",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                    "metric_name": "val_bpb",
                    "metric_value": 1.11,
                    "direction": "min",
                    "status": "success",
                },
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "claim.asserted",
                "workspace_id": workspace_id,
                "aggregate_id": "claim-feedback",
                "aggregate_kind": "claim",
                "payload": {
                    "claim_id": "claim-feedback",
                    "statement": "Feedback validation claim",
                    "claim_type": "improvement",
                    "candidate_snapshot_id": "snap-feedback",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "evidence_run_ids": ["run-feedback"],
                },
            },
        ).status_code
        == 201
    )

    response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.reproduced",
            "workspace_id": workspace_id,
            "aggregate_id": "claim-feedback",
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": "claim-feedback",
                "evidence_run_id": "run-does-not-exist",
            },
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "claim.reproduced evidence_run_id must reference a known workspace run"
    )
