from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_schema(name: str) -> dict[str, object]:
    path = REPO_ROOT / "schemas" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_node_identity_schema_declares_first_mesh_identity_contract() -> None:
    schema = _load_schema("node-identity.schema.json")

    assert schema["$id"] == "https://research-os.local/schemas/node-identity.schema.json"
    assert schema["properties"]["identity_schema"]["const"] == "openintention-node-identity-v1"
    assert schema["properties"]["identity_version"]["const"] == 1
    assert "signing_keys" in schema["required"]
    assert "capabilities" in schema["required"]
    assert "node_heartbeat" in schema["properties"]["capabilities"]["items"]["enum"]
    assert "lease_fail" in schema["properties"]["capabilities"]["items"]["enum"]
    assert "lease_complete" in schema["properties"]["capabilities"]["items"]["enum"]


def test_network_envelope_schema_preserves_signed_transport_boundary() -> None:
    schema = _load_schema("network-envelope.schema.json")

    assert schema["properties"]["envelope_schema"]["const"] == "openintention-network-envelope-v1"
    assert schema["properties"]["message_type"]["enum"] == [
        "event.append",
        "lease.acquire",
        "lease.renew",
        "lease.release",
        "lease.fail",
        "lease.complete",
        "node.heartbeat",
    ]
    assert schema["properties"]["payload_digest"]["pattern"] == "^sha256:[0-9a-f]{64}$"
    assert schema["properties"]["signature_scheme"]["enum"] == ["ed25519"]


def test_lease_schemas_define_bounded_coordination_contract() -> None:
    lease_schema = _load_schema("lease.schema.json")
    command_schema = _load_schema("lease-command.schema.json")

    assert lease_schema["properties"]["lease_schema"]["const"] == "openintention-lease-v1"
    assert lease_schema["properties"]["status"]["enum"] == [
        "available",
        "acquired",
        "renewed",
        "released",
        "completed",
        "failed",
        "expired",
    ]
    assert command_schema["properties"]["command_schema"]["const"] == "openintention-lease-command-v1"
    assert command_schema["properties"]["action"]["enum"] == [
        "acquire",
        "renew",
        "release",
        "fail",
        "complete",
        "heartbeat",
    ]
    assert "completed_at" in lease_schema["properties"]
    assert "failure_reason" in lease_schema["properties"]
    assert "stale_completion" in lease_schema["properties"]
    assert "work_item_type" in command_schema["properties"]
    assert "subject_type" in command_schema["properties"]
    assert "subject_id" in command_schema["properties"]


def test_node_heartbeat_schema_defines_coordination_read_contract() -> None:
    schema = _load_schema("node-heartbeat.schema.json")

    assert schema["$id"] == "https://research-os.local/schemas/node-heartbeat.schema.json"
    assert schema["properties"]["heartbeat_schema"]["const"] == "openintention-node-heartbeat-v1"
    assert schema["properties"]["heartbeat_version"]["const"] == 1
    assert schema["properties"]["freshness_status"]["enum"] == ["fresh", "stale"]
    assert "node_id" in schema["required"]
    assert "expires_at" in schema["required"]


def test_domain_model_records_mesh_foundation_types() -> None:
    domain_model = (REPO_ROOT / "spec" / "domain-model.yaml").read_text(encoding="utf-8")

    assert "NodeIdentity:" in domain_model
    assert "NetworkEnvelope:" in domain_model
    assert "NodeHeartbeat:" in domain_model
    assert "Lease:" in domain_model
    assert "LeaseState:" in domain_model
