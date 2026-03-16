from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from apps.api.main import create_app
from research_os.settings import Settings


SIGNED_LEASE_NODE_ID = "node_alphaworker000001"


def test_signed_lease_acquire_renew_and_release_round_trip(tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_lease_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    _, verifier_workspace_id, recommendation = _seed_claim_and_recommendation(client)

    acquire_envelope = _build_signed_lease_envelope(
        private_key=private_key,
        message_type="lease.acquire",
        request_id="lease-signed-acquire-1",
        payload={
            "request_id": "lease-signed-acquire-1",
            "node_id": SIGNED_LEASE_NODE_ID,
            "planner_fingerprint": recommendation["planner_fingerprint"],
            "ttl_seconds": 120,
            "participant_role": "verifier",
            "work_item_type": recommendation["work_item_type"],
            "subject_type": recommendation["subject_type"],
            "subject_id": recommendation["subject_id"],
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "workspace_id": verifier_workspace_id,
        },
    )

    acquire_response = client.post("/api/v1/leases/acquire", json=acquire_envelope)
    assert acquire_response.status_code == 200
    lease = acquire_response.json()
    assert lease["status"] == "acquired"

    renew_envelope = _build_signed_lease_envelope(
        private_key=private_key,
        message_type="lease.renew",
        request_id="lease-signed-renew-1",
        payload={
            "request_id": "lease-signed-renew-1",
            "node_id": SIGNED_LEASE_NODE_ID,
            "ttl_seconds": 60,
        },
    )
    renew_response = client.post(f"/api/v1/leases/{lease['lease_id']}/renew", json=renew_envelope)
    assert renew_response.status_code == 200
    assert renew_response.json()["status"] == "renewed"

    release_envelope = _build_signed_lease_envelope(
        private_key=private_key,
        message_type="lease.release",
        request_id="lease-signed-release-1",
        payload={
            "request_id": "lease-signed-release-1",
            "node_id": SIGNED_LEASE_NODE_ID,
        },
    )
    release_response = client.post(f"/api/v1/leases/{lease['lease_id']}/release", json=release_envelope)
    assert release_response.status_code == 200
    assert release_response.json()["status"] == "released"


def test_signed_lease_complete_preserves_verifier_lineage_requirement(tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_lease_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    _, verifier_workspace_id, recommendation = _seed_claim_and_recommendation(client)

    acquire_envelope = _build_signed_lease_envelope(
        private_key=private_key,
        message_type="lease.acquire",
        request_id="lease-signed-complete-acquire-1",
        payload={
            "request_id": "lease-signed-complete-acquire-1",
            "node_id": SIGNED_LEASE_NODE_ID,
            "planner_fingerprint": recommendation["planner_fingerprint"],
            "ttl_seconds": 120,
            "participant_role": "verifier",
            "work_item_type": recommendation["work_item_type"],
            "subject_type": recommendation["subject_type"],
            "subject_id": recommendation["subject_id"],
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "workspace_id": verifier_workspace_id,
        },
    )
    acquire_response = client.post("/api/v1/leases/acquire", json=acquire_envelope)
    lease_id = acquire_response.json()["lease_id"]

    _append_snapshot(client, workspace_id=verifier_workspace_id, snapshot_id="signed-verifier-snap-1")
    _append_run(
        client,
        workspace_id=verifier_workspace_id,
        snapshot_id="signed-verifier-snap-1",
        run_id="signed-verifier-run-1",
    )
    _append_reproduction(
        client,
        workspace_id=verifier_workspace_id,
        claim_id="signed-claim-1",
        run_id="signed-verifier-run-1",
    )

    complete_envelope = _build_signed_lease_envelope(
        private_key=private_key,
        message_type="lease.complete",
        request_id="lease-signed-complete-1",
        payload={
            "request_id": "lease-signed-complete-1",
            "node_id": SIGNED_LEASE_NODE_ID,
            "workspace_id": verifier_workspace_id,
            "observed_run_id": "signed-verifier-run-1",
            "observed_claim_id": "signed-claim-1",
        },
    )
    complete_response = client.post(f"/api/v1/leases/{lease_id}/complete", json=complete_envelope)
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"
    assert complete_response.json()["observed_claim_id"] == "signed-claim-1"


def test_signed_lease_rejects_replay(tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_lease_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    _, verifier_workspace_id, recommendation = _seed_claim_and_recommendation(client)

    envelope = _build_signed_lease_envelope(
        private_key=private_key,
        envelope_id="lease-replay-env-1",
        request_id="lease-replay-req-1",
        message_type="lease.acquire",
        payload={
            "request_id": "lease-replay-req-1",
            "node_id": SIGNED_LEASE_NODE_ID,
            "planner_fingerprint": recommendation["planner_fingerprint"],
            "ttl_seconds": 120,
            "participant_role": "verifier",
            "work_item_type": recommendation["work_item_type"],
            "subject_type": recommendation["subject_type"],
            "subject_id": recommendation["subject_id"],
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "workspace_id": verifier_workspace_id,
        },
    )

    first_response = client.post("/api/v1/leases/acquire", json=envelope)
    replay_response = client.post("/api/v1/leases/acquire", json=envelope)

    assert first_response.status_code == 200
    assert replay_response.status_code == 409
    assert replay_response.json()["detail"] == "network envelope lease-replay-env-1 already accepted"


def test_signed_lease_rejects_missing_capability(tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_lease_settings(
        tmp_path,
        private_key=private_key,
        capabilities=["event_append"],
    )
    client = TestClient(create_app(settings))
    _, verifier_workspace_id, recommendation = _seed_claim_and_recommendation(client)

    envelope = _build_signed_lease_envelope(
        private_key=private_key,
        message_type="lease.acquire",
        request_id="lease-no-cap-1",
        payload={
            "request_id": "lease-no-cap-1",
            "node_id": SIGNED_LEASE_NODE_ID,
            "planner_fingerprint": recommendation["planner_fingerprint"],
            "ttl_seconds": 120,
            "participant_role": "verifier",
            "work_item_type": recommendation["work_item_type"],
            "subject_type": recommendation["subject_type"],
            "subject_id": recommendation["subject_id"],
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "workspace_id": verifier_workspace_id,
        },
    )

    response = client.post("/api/v1/leases/acquire", json=envelope)
    assert response.status_code == 400
    assert response.json()["detail"] == "sender_node_id is not authorized for lease.acquire capability"


def _build_signed_lease_settings(
    tmp_path,
    *,
    private_key: Ed25519PrivateKey,
    capabilities: list[str] | None = None,
) -> Settings:
    trusted_nodes_path = tmp_path / "trusted-lease-nodes.json"
    public_key = private_key.public_key().public_bytes_raw()
    trusted_nodes = [
        {
            "node_id": SIGNED_LEASE_NODE_ID,
            "identity_schema": "openintention-node-identity-v1",
            "identity_version": 1,
            "display_name": "Node Alpha",
            "signing_keys": [
                {
                    "key_id": "key-alpha-1",
                    "public_key": base64.b64encode(public_key).decode("ascii"),
                    "signature_scheme": "ed25519",
                    "status": "active",
                }
            ],
            "capabilities": capabilities
            or [
                "lease_acquire",
                "lease_renew",
                "lease_release",
                "lease_fail",
                "lease_complete",
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    trusted_nodes_json = json.dumps(trusted_nodes, sort_keys=True)
    trusted_nodes_path.write_text(trusted_nodes_json, encoding="utf-8")
    return Settings(
        db_path=str(tmp_path / "signed-lease.db"),
        artifact_root=str(tmp_path / "artifacts"),
        network_trusted_nodes_path=str(trusted_nodes_path),
    )


def _seed_claim_and_recommendation(client: TestClient) -> tuple[str, str, dict[str, object]]:
    source_workspace_id = _create_workspace(client, name="signed-source-worker")
    verifier_workspace_id = _create_workspace(
        client,
        name="signed-verifier-worker",
        participant_role="verifier",
    )
    _append_snapshot(client, workspace_id=source_workspace_id, snapshot_id="signed-snap-1")
    _append_run(
        client,
        workspace_id=source_workspace_id,
        run_id="signed-run-1",
        snapshot_id="signed-snap-1",
    )
    _append_claim(
        client,
        workspace_id=source_workspace_id,
        claim_id="signed-claim-1",
        snapshot_id="signed-snap-1",
        run_id="signed-run-1",
    )
    planner_response = client.post(
        "/api/v1/planner/recommend",
        json={
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "target_claim_id": "signed-claim-1",
            "limit": 1,
        },
    )
    assert planner_response.status_code == 200
    return source_workspace_id, verifier_workspace_id, planner_response.json()["recommendations"][0]


def _create_workspace(
    client: TestClient,
    *,
    name: str,
    participant_role: str = "contributor",
) -> str:
    response = client.post(
        "/api/v1/workspaces",
        json={
            "name": name,
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "participant_role": participant_role,
            "actor_id": name,
        },
    )
    assert response.status_code == 201
    return response.json()["workspace_id"]


def _append_snapshot(client: TestClient, *, workspace_id: str, snapshot_id: str) -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": snapshot_id,
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": snapshot_id,
                "artifact_uri": "artifact://sha256/" + "a" * 64,
            },
        },
    )
    assert response.status_code == 201


def _append_run(
    client: TestClient,
    *,
    workspace_id: str,
    run_id: str,
    snapshot_id: str,
) -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "kind": "run.completed",
            "workspace_id": workspace_id,
            "aggregate_id": run_id,
            "aggregate_kind": "run",
            "payload": {
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.1,
                "direction": "min",
                "status": "success",
            },
        },
    )
    assert response.status_code == 201


def _append_claim(client: TestClient, *, workspace_id: str, claim_id: str, snapshot_id: str, run_id: str) -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.asserted",
            "workspace_id": workspace_id,
            "aggregate_id": claim_id,
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": claim_id,
                "statement": "Signed lease claim.",
                "claim_type": "improvement",
                "candidate_snapshot_id": snapshot_id,
                "objective": "val_bpb",
                "platform": "A100",
                "metric_name": "val_bpb",
                "delta": -0.01,
                "evidence_run_ids": [run_id],
            },
        },
    )
    assert response.status_code == 201


def _append_reproduction(client: TestClient, *, workspace_id: str, claim_id: str, run_id: str) -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.reproduced",
            "workspace_id": workspace_id,
            "aggregate_id": claim_id,
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": claim_id,
                "evidence_run_id": run_id,
            },
        },
    )
    assert response.status_code == 201


def _build_signed_lease_envelope(
    *,
    private_key: Ed25519PrivateKey,
    message_type: str,
    request_id: str,
    payload: dict[str, object],
    envelope_id: str | None = None,
) -> dict[str, object]:
    envelope_id = envelope_id or f"env-{request_id}"
    envelope: dict[str, object] = {
        "envelope_id": envelope_id,
        "envelope_schema": "openintention-network-envelope-v1",
        "envelope_version": 1,
        "message_type": message_type,
        "sender_node_id": SIGNED_LEASE_NODE_ID,
        "sender_key_id": "key-alpha-1",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        "payload_schema": "research_os.lease-command.v1",
        "payload_digest": _canonical_payload_digest(payload),
        "payload": payload,
        "signature_scheme": "ed25519",
        "request_id": request_id,
        "trace_id": f"trace-{request_id}",
        "replay_window_seconds": 300,
    }
    signature = private_key.sign(_canonical_json_bytes(envelope))
    envelope["signature"] = base64.b64encode(signature).decode("ascii")
    return envelope


def _canonical_payload_digest(payload: dict[str, object]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
