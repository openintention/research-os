from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research_os.domain.models import NetworkMessageType, SignatureScheme, SignedNetworkEnvelope
from research_os.network.ingress import canonical_json_bytes, canonical_payload_digest


@dataclass(frozen=True, slots=True)
class LocalNodeSigner:
    node_id: str
    key_id: str
    private_key: Ed25519PrivateKey


def load_local_node_signer(
    *,
    node_id: str,
    key_id: str,
    private_key_path: str | Path,
) -> LocalNodeSigner:
    key_path = Path(private_key_path)
    key_bytes = key_path.read_bytes()
    private_key = _load_private_key(key_bytes)
    return LocalNodeSigner(
        node_id=node_id,
        key_id=key_id,
        private_key=private_key,
    )


def build_signed_envelope(
    *,
    signer: LocalNodeSigner,
    message_type: NetworkMessageType,
    payload_schema: str,
    payload: dict[str, object],
    request_id: str,
    envelope_id: str,
    sent_at: datetime,
    expires_at: datetime | None = None,
    replay_window_seconds: int | None = None,
    trace_id: str | None = None,
) -> dict[str, object]:
    unsigned_candidate = {
        "envelope_id": envelope_id,
        "envelope_schema": "openintention-network-envelope-v1",
        "envelope_version": 1,
        "message_type": message_type,
        "sender_node_id": signer.node_id,
        "sender_key_id": signer.key_id,
        "sent_at": sent_at,
        "expires_at": expires_at,
        "payload_schema": payload_schema,
        "payload_digest": canonical_payload_digest(payload),
        "payload": payload,
        "signature_scheme": SignatureScheme.ED25519,
        "request_id": request_id,
        "trace_id": trace_id,
        "replay_window_seconds": replay_window_seconds,
    }
    validated_unsigned = SignedNetworkEnvelope.model_validate(
        {
            **unsigned_candidate,
            "signature": base64.b64encode(b"\x00" * 64).decode("ascii"),
        }
    )
    canonical_envelope = validated_unsigned.model_dump(mode="json")
    canonical_envelope.pop("signature", None)
    signature = signer.private_key.sign(canonical_json_bytes(canonical_envelope))
    validated_signed = SignedNetworkEnvelope.model_validate(
        {
            **canonical_envelope,
            "signature": base64.b64encode(signature).decode("ascii"),
        }
    )
    return validated_signed.model_dump(mode="json")


def _load_private_key(key_bytes: bytes) -> Ed25519PrivateKey:
    stripped = key_bytes.strip()
    if stripped.startswith(b"-----BEGIN"):
        private_key = serialization.load_pem_private_key(stripped, password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("private key must be an Ed25519 PEM key")
        return private_key

    candidate = stripped
    try:
        decoded = base64.b64decode(candidate, validate=True)
    except ValueError:
        decoded = candidate

    if len(decoded) != 32:
        raise ValueError("private key must be PEM or base64/raw 32-byte Ed25519 key material")
    return Ed25519PrivateKey.from_private_bytes(decoded)
