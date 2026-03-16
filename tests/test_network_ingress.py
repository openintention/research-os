from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from apps.api.main import create_app
from research_os.artifacts.local import LocalArtifactRegistry
from research_os.settings import Settings


def test_append_event_accepts_valid_signed_network_envelope(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_ingress_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"signed envelope snapshot")
    workspace_id = _create_workspace(client)

    envelope = _build_event_append_envelope(
        private_key=private_key,
        payload={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-signed-1",
            "aggregate_kind": "snapshot",
            "actor_id": "node-alpha",
            "payload": {
                "snapshot_id": "snap-signed-1",
                "parent_snapshot_ids": ["snap-baseline"],
                "artifact_uri": snapshot_artifact.uri,
            },
            "tags": {"channel": "signed-ingress"},
        },
    )

    response = client.post("/api/v1/events", json=envelope)

    assert response.status_code == 201
    assert response.json()["event_id"] == envelope["payload"]["event_id"]

    events = client.get(f"/api/v1/events?workspace_id={workspace_id}&kind=snapshot.published")
    assert events.status_code == 200
    assert events.json()[0]["payload"]["artifact_uri"] == snapshot_artifact.uri


def test_append_event_accepts_inline_trusted_node_json(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_ingress_settings(tmp_path, private_key=private_key, inline_config=True)
    client = TestClient(create_app(settings))
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"signed envelope snapshot")
    workspace_id = _create_workspace(client)

    envelope = _build_event_append_envelope(
        private_key=private_key,
        payload={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-inline-config-1",
            "aggregate_kind": "snapshot",
            "actor_id": "node-alpha",
            "payload": {
                "snapshot_id": "snap-inline-config-1",
                "artifact_uri": snapshot_artifact.uri,
            },
            "tags": {},
        },
    )

    response = client.post("/api/v1/events", json=envelope)

    assert response.status_code == 201


def test_append_event_rejects_signed_network_envelope_with_wrong_digest(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_ingress_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"signed envelope snapshot")
    workspace_id = _create_workspace(client)

    envelope = _build_event_append_envelope(
        private_key=private_key,
        payload={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-signed-bad-digest",
            "aggregate_kind": "snapshot",
            "actor_id": "node-alpha",
            "payload": {
                "snapshot_id": "snap-signed-bad-digest",
                "artifact_uri": snapshot_artifact.uri,
            },
            "tags": {},
        },
    )
    envelope["payload_digest"] = "sha256:" + ("0" * 64)

    response = client.post("/api/v1/events", json=envelope)

    assert response.status_code == 400
    assert response.json()["detail"] == "payload_digest does not match canonical payload"


def test_append_event_rejects_signed_network_envelope_with_invalid_signature(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_ingress_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"signed envelope snapshot")
    workspace_id = _create_workspace(client)

    envelope = _build_event_append_envelope(
        private_key=private_key,
        payload={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-signed-bad-signature",
            "aggregate_kind": "snapshot",
            "actor_id": "node-alpha",
            "payload": {
                "snapshot_id": "snap-signed-bad-signature",
                "artifact_uri": snapshot_artifact.uri,
            },
            "tags": {},
        },
    )
    envelope["signature"] = base64.b64encode(b"not-a-valid-ed25519-signature").decode("ascii")

    response = client.post("/api/v1/events", json=envelope)

    assert response.status_code == 400
    assert response.json()["detail"] == "signature is invalid for canonical envelope payload"


def test_append_event_rejects_signed_network_envelope_with_unknown_sender_key(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_ingress_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"signed envelope snapshot")
    workspace_id = _create_workspace(client)

    envelope = _build_event_append_envelope(
        private_key=private_key,
        sender_node_id="node_unknownsender0001",
        sender_key_id="missing-key",
        payload={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-signed-unknown-sender",
            "aggregate_kind": "snapshot",
            "actor_id": "node-alpha",
            "payload": {
                "snapshot_id": "snap-signed-unknown-sender",
                "artifact_uri": snapshot_artifact.uri,
            },
            "tags": {},
        },
    )

    response = client.post("/api/v1/events", json=envelope)

    assert response.status_code == 400
    assert response.json()["detail"] == "sender_node_id is not trusted for signed ingress"


def test_append_event_rejects_signed_network_envelope_with_unknown_key_id(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_ingress_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"signed envelope snapshot")
    workspace_id = _create_workspace(client)

    envelope = _build_event_append_envelope(
        private_key=private_key,
        sender_key_id="missing-key",
        payload={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-signed-unknown-key",
            "aggregate_kind": "snapshot",
            "actor_id": "node-alpha",
            "payload": {
                "snapshot_id": "snap-signed-unknown-key",
                "artifact_uri": snapshot_artifact.uri,
            },
            "tags": {},
        },
    )

    response = client.post("/api/v1/events", json=envelope)

    assert response.status_code == 400
    assert response.json()["detail"] == "sender_key_id is not known for trusted sender"


def test_append_event_rejects_replayed_signed_network_envelope(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_ingress_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"signed envelope snapshot")
    workspace_id = _create_workspace(client)

    envelope = _build_event_append_envelope(
        private_key=private_key,
        envelope_id="env-replay-1",
        request_id="req-replay-1",
        payload={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": "snap-signed-replay",
            "aggregate_kind": "snapshot",
            "actor_id": "node-alpha",
            "payload": {
                "snapshot_id": "snap-signed-replay",
                "artifact_uri": snapshot_artifact.uri,
            },
            "tags": {},
        },
    )

    first_response = client.post("/api/v1/events", json=envelope)
    replay_response = client.post("/api/v1/events", json=envelope)

    assert first_response.status_code == 201
    assert replay_response.status_code == 409
    assert replay_response.json()["detail"] == "network envelope env-replay-1 already accepted"


def test_signed_network_envelope_still_flows_through_event_validation(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    settings = _build_signed_ingress_settings(tmp_path, private_key=private_key)
    client = TestClient(create_app(settings))
    workspace_id = _create_workspace(client)

    envelope = _build_event_append_envelope(
        private_key=private_key,
        payload={
            "kind": "run.completed",
            "workspace_id": workspace_id,
            "aggregate_id": "run-signed-invalid",
            "aggregate_kind": "run",
            "actor_id": "node-alpha",
            "payload": {
                "run_id": "run-signed-invalid",
                "snapshot_id": "snap-missing",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.11,
                "direction": "min",
                "status": "success",
            },
            "tags": {},
        },
    )

    response = client.post("/api/v1/events", json=envelope)

    assert response.status_code == 400
    assert response.json()["detail"] == "run.completed snapshot_id must reference a known workspace snapshot"


def _build_signed_ingress_settings(
    tmp_path,
    *,
    private_key: Ed25519PrivateKey,
    inline_config: bool = False,
) -> Settings:
    trusted_nodes_path = tmp_path / "trusted-nodes.json"
    public_key = private_key.public_key().public_bytes_raw()
    trusted_nodes = [
        {
            "node_id": "node_alpha0000000001",
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
            "capabilities": ["event_append"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    trusted_nodes_json = json.dumps(trusted_nodes, sort_keys=True)
    trusted_nodes_path.write_text(trusted_nodes_json, encoding="utf-8")

    return Settings(
        db_path=str(tmp_path / "signed-ingress.db"),
        artifact_root=str(tmp_path / "artifacts"),
        network_trusted_nodes_path=None if inline_config else str(trusted_nodes_path),
        network_trusted_nodes_json=trusted_nodes_json if inline_config else None,
    )


def _create_workspace(client: TestClient) -> str:
    response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "signed-ingress-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "actor_id": "workspace-owner",
        },
    )
    assert response.status_code == 201
    return response.json()["workspace_id"]


def _build_event_append_envelope(
    *,
    private_key: Ed25519PrivateKey,
    payload: dict[str, object],
    envelope_id: str = "env-1",
    sender_node_id: str = "node_alpha0000000001",
    sender_key_id: str = "key-alpha-1",
    request_id: str = "req-1",
) -> dict[str, object]:
    event_payload = {"event_id": f"{envelope_id}-event", **payload}
    envelope: dict[str, object] = {
        "envelope_id": envelope_id,
        "envelope_schema": "openintention-network-envelope-v1",
        "envelope_version": 1,
        "message_type": "event.append",
        "sender_node_id": sender_node_id,
        "sender_key_id": sender_key_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        "payload_schema": "research_os.event-envelope.v1",
        "payload_digest": _canonical_payload_digest(event_payload),
        "payload": event_payload,
        "signature_scheme": "ed25519",
        "request_id": request_id,
        "trace_id": f"trace-{envelope_id}",
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
