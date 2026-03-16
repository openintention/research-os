from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from apps.api.main import create_app
from research_os.settings import Settings


SIGNED_HEARTBEAT_NODE_ID = "node_heartbeatworker01"


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, *, seconds: int) -> None:
        self._now = self._now + timedelta(seconds=seconds)


def test_signed_heartbeat_updates_lease_liveness_and_turns_stale(tmp_path) -> None:
    clock = MutableClock(datetime(2026, 3, 16, tzinfo=timezone.utc))
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_heartbeat_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings, now_fn=clock.now))
    lease_id = _acquire_verifier_lease(client, node_id=SIGNED_HEARTBEAT_NODE_ID)

    missing_response = client.get(f"/api/v1/leases/{lease_id}")
    assert missing_response.status_code == 200
    assert missing_response.json()["liveness_status"] == "missing"
    assert missing_response.json()["holder_heartbeat"] is None

    heartbeat_envelope = _build_signed_heartbeat_envelope(
        private_key=private_key,
        request_id="heartbeat-signed-1",
        ttl_seconds=30,
    )
    heartbeat_response = client.post("/api/v1/network/heartbeats", json=heartbeat_envelope)
    assert heartbeat_response.status_code == 201
    heartbeat = heartbeat_response.json()
    assert heartbeat["node_id"] == SIGNED_HEARTBEAT_NODE_ID
    assert heartbeat["freshness_status"] == "fresh"

    heartbeat_read = client.get(f"/api/v1/network/heartbeats/{SIGNED_HEARTBEAT_NODE_ID}")
    assert heartbeat_read.status_code == 200
    assert heartbeat_read.json()["freshness_status"] == "fresh"

    lease_view = client.get(f"/api/v1/leases/{lease_id}")
    assert lease_view.status_code == 200
    assert lease_view.json()["liveness_status"] == "healthy"
    assert lease_view.json()["holder_heartbeat"]["node_id"] == SIGNED_HEARTBEAT_NODE_ID

    clock.advance(seconds=31)

    stale_heartbeat = client.get(f"/api/v1/network/heartbeats/{SIGNED_HEARTBEAT_NODE_ID}")
    assert stale_heartbeat.status_code == 200
    assert stale_heartbeat.json()["freshness_status"] == "stale"

    stale_lease = client.get(f"/api/v1/leases/{lease_id}")
    assert stale_lease.status_code == 200
    assert stale_lease.json()["liveness_status"] == "stale"
    assert stale_lease.json()["lease"]["status"] == "acquired"


def test_signed_heartbeat_rejects_replay(tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_heartbeat_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))

    envelope = _build_signed_heartbeat_envelope(
        private_key=private_key,
        envelope_id="heartbeat-replay-env-1",
        request_id="heartbeat-replay-1",
        ttl_seconds=45,
    )

    first_response = client.post("/api/v1/network/heartbeats", json=envelope)
    replay_response = client.post("/api/v1/network/heartbeats", json=envelope)

    assert first_response.status_code == 201
    assert replay_response.status_code == 409
    assert replay_response.json()["detail"] == "network envelope heartbeat-replay-env-1 already accepted"


def test_signed_heartbeat_rejects_missing_capability(tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_heartbeat_settings(
        tmp_path,
        private_key=private_key,
        capabilities=["lease_acquire"],
    )
    client = TestClient(create_app(settings))

    envelope = _build_signed_heartbeat_envelope(
        private_key=private_key,
        request_id="heartbeat-no-cap-1",
        ttl_seconds=45,
    )

    response = client.post("/api/v1/network/heartbeats", json=envelope)
    assert response.status_code == 400
    assert response.json()["detail"] == "sender_node_id is not authorized for node.heartbeat capability"


def _build_signed_heartbeat_settings(
    tmp_path,
    *,
    private_key: Ed25519PrivateKey,
    capabilities: list[str] | None = None,
) -> Settings:
    trusted_nodes_path = tmp_path / "trusted-heartbeat-nodes.json"
    public_key = private_key.public_key().public_bytes_raw()
    trusted_nodes = [
        {
            "node_id": SIGNED_HEARTBEAT_NODE_ID,
            "identity_schema": "openintention-node-identity-v1",
            "identity_version": 1,
            "display_name": "Heartbeat Node",
            "signing_keys": [
                {
                    "key_id": "key-heartbeat-1",
                    "public_key": base64.b64encode(public_key).decode("ascii"),
                    "signature_scheme": "ed25519",
                    "status": "active",
                }
            ],
            "capabilities": capabilities or ["node_heartbeat"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    trusted_nodes_path.write_text(json.dumps(trusted_nodes, sort_keys=True), encoding="utf-8")
    return Settings(
        db_path=str(tmp_path / "signed-heartbeat.db"),
        artifact_root=str(tmp_path / "artifacts"),
        network_trusted_nodes_path=str(trusted_nodes_path),
    )


def _acquire_verifier_lease(client: TestClient, *, node_id: str) -> str:
    source_workspace_id = _create_workspace(client, name="heartbeat-source-worker")
    verifier_workspace_id = _create_workspace(
        client,
        name="heartbeat-verifier-worker",
        participant_role="verifier",
    )
    _append_snapshot(client, workspace_id=source_workspace_id, snapshot_id="heartbeat-snap-1")
    _append_run(
        client,
        workspace_id=source_workspace_id,
        snapshot_id="heartbeat-snap-1",
        run_id="heartbeat-run-1",
    )
    _append_claim(
        client,
        workspace_id=source_workspace_id,
        claim_id="heartbeat-claim-1",
        snapshot_id="heartbeat-snap-1",
        run_id="heartbeat-run-1",
    )
    planner_response = client.post(
        "/api/v1/planner/recommend",
        json={
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "target_claim_id": "heartbeat-claim-1",
            "limit": 1,
        },
    )
    assert planner_response.status_code == 200
    recommendation = planner_response.json()["recommendations"][0]
    acquire_response = client.post(
        "/api/v1/leases/acquire",
        json={
            "request_id": "heartbeat-lease-acquire-1",
            "node_id": node_id,
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
    assert acquire_response.status_code == 200
    return acquire_response.json()["lease_id"]


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
                "metric_value": 1.11,
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
                "statement": "Heartbeat claim.",
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


def _build_signed_heartbeat_envelope(
    *,
    private_key: Ed25519PrivateKey,
    request_id: str,
    ttl_seconds: int,
    envelope_id: str | None = None,
) -> dict[str, object]:
    payload = {
        "heartbeat_schema": "openintention-node-heartbeat-v1",
        "heartbeat_version": 1,
        "request_id": request_id,
        "node_id": SIGNED_HEARTBEAT_NODE_ID,
        "ttl_seconds": ttl_seconds,
    }
    envelope_id = envelope_id or f"env-{request_id}"
    envelope: dict[str, object] = {
        "envelope_id": envelope_id,
        "envelope_schema": "openintention-network-envelope-v1",
        "envelope_version": 1,
        "message_type": "node.heartbeat",
        "sender_node_id": SIGNED_HEARTBEAT_NODE_ID,
        "sender_key_id": "key-heartbeat-1",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        "payload_schema": "research_os.node-heartbeat.v1",
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
