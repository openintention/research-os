from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research_os.domain.models import (
    LeaseCommandAction,
    NetworkMessageType,
    SignedNetworkEnvelope,
)
from research_os.network.ingress import LeaseCommandIngressVerifier, TrustedNodeRegistry
from research_os.network.signing import LocalNodeSigner, build_signed_envelope
from research_os.network.sqlite import SQLiteNetworkEnvelopeStore


def test_build_signed_envelope_round_trips_through_lease_verifier(tmp_path) -> None:
    now = datetime(2026, 3, 16, tzinfo=timezone.utc)
    private_key = Ed25519PrivateKey.generate()
    signer = LocalNodeSigner(
        node_id="node_signingroundtrip01",
        key_id="signing-roundtrip-key-1",
        private_key=private_key,
    )
    registry = TrustedNodeRegistry.from_sources(
        inline_json=json.dumps(
            [
                {
                    "node_id": signer.node_id,
                    "identity_schema": "openintention-node-identity-v1",
                    "identity_version": 1,
                    "display_name": "Signing Roundtrip Node",
                    "signing_keys": [
                        {
                            "key_id": signer.key_id,
                            "public_key": base64.b64encode(
                                private_key.public_key().public_bytes_raw()
                            ).decode("ascii"),
                            "signature_scheme": "ed25519",
                            "status": "active",
                        }
                    ],
                    "capabilities": ["lease_acquire"],
                    "created_at": now.isoformat(),
                }
            ],
            sort_keys=True,
        )
    )
    verifier = LeaseCommandIngressVerifier(
        trusted_nodes=registry,
        receipt_store=SQLiteNetworkEnvelopeStore(str(tmp_path / "receipts.db")),
        now_fn=lambda: now,
    )
    payload = {
        "command_schema": "openintention-lease-command-v1",
        "command_version": 1,
        "request_id": "lease-signing-roundtrip-1",
        "node_id": signer.node_id,
        "planner_fingerprint": "sha256:" + ("1" * 64),
        "ttl_seconds": 120,
        "participant_role": "contributor",
        "work_item_type": "explore_effort",
        "subject_type": "effort",
        "subject_id": "effort-mlx",
        "effort_id": "effort-mlx",
        "objective": "val_bpb",
        "platform": "A100",
        "budget_seconds": 300,
    }
    raw_envelope = build_signed_envelope(
        signer=signer,
        message_type=NetworkMessageType.LEASE_ACQUIRE,
        payload_schema="openintention-lease-command-v1",
        payload=payload,
        request_id="lease-signing-roundtrip-1",
        envelope_id="env-lease-signing-roundtrip-1",
        sent_at=now,
        expires_at=now + timedelta(minutes=5),
        replay_window_seconds=300,
        trace_id="trace-lease-signing-roundtrip-1",
    )

    command = verifier.verify(
        SignedNetworkEnvelope.model_validate(raw_envelope),
        raw_envelope=raw_envelope,
    )

    assert command.action is LeaseCommandAction.ACQUIRE
    assert command.node_id == signer.node_id
    assert command.subject_id == "effort-mlx"
