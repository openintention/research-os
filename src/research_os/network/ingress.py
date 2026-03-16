from __future__ import annotations

import base64
from binascii import Error as BinasciiError
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import TypeVar

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import ValidationError

from research_os.domain.models import (
    EventEnvelope,
    LeaseCommand,
    LeaseCommandAction,
    NetworkMessageType,
    NodeCapability,
    NodeIdentity,
    SignedNetworkEnvelope,
    SigningKeyStatus,
)
from research_os.network.sqlite import SQLiteNetworkEnvelopeStore


class EnvelopeVerificationError(ValueError):
    pass


class EnvelopeReplayError(RuntimeError):
    pass


T = TypeVar("T")


_LEASE_MESSAGE_CAPABILITIES: dict[NetworkMessageType, NodeCapability] = {
    NetworkMessageType.LEASE_ACQUIRE: NodeCapability.LEASE_ACQUIRE,
    NetworkMessageType.LEASE_RENEW: NodeCapability.LEASE_RENEW,
    NetworkMessageType.LEASE_RELEASE: NodeCapability.LEASE_RELEASE,
    NetworkMessageType.LEASE_FAIL: NodeCapability.LEASE_FAIL,
    NetworkMessageType.LEASE_COMPLETE: NodeCapability.LEASE_COMPLETE,
}

_LEASE_MESSAGE_ACTIONS: dict[NetworkMessageType, LeaseCommandAction] = {
    NetworkMessageType.LEASE_ACQUIRE: LeaseCommandAction.ACQUIRE,
    NetworkMessageType.LEASE_RENEW: LeaseCommandAction.RENEW,
    NetworkMessageType.LEASE_RELEASE: LeaseCommandAction.RELEASE,
    NetworkMessageType.LEASE_FAIL: LeaseCommandAction.FAIL,
    NetworkMessageType.LEASE_COMPLETE: LeaseCommandAction.COMPLETE,
}


class TrustedNodeRegistry:
    def __init__(self, nodes: dict[str, NodeIdentity]) -> None:
        self._nodes = nodes

    @classmethod
    def from_sources(
        cls,
        *,
        path: str | None = None,
        inline_json: str | None = None,
    ) -> "TrustedNodeRegistry":
        if inline_json is not None:
            raw = json.loads(inline_json)
        elif path is not None:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        else:
            return cls({})
        if isinstance(raw, list):
            node_documents = raw
        elif isinstance(raw, dict) and "nodes" in raw:
            node_documents = raw["nodes"]
        else:
            node_documents = [raw]

        nodes = {node.node_id: node for node in (NodeIdentity.model_validate(item) for item in node_documents)}
        return cls(nodes)

    def get(self, node_id: str) -> NodeIdentity | None:
        return self._nodes.get(node_id)


class EventAppendIngressVerifier:
    def __init__(
        self,
        *,
        trusted_nodes: TrustedNodeRegistry,
        receipt_store: SQLiteNetworkEnvelopeStore,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.trusted_nodes = trusted_nodes
        self.receipt_store = receipt_store
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self.receipt_store.init_schema()

    def verify_and_record(
        self,
        envelope: SignedNetworkEnvelope,
        *,
        raw_envelope: dict[str, object],
        append_event: Callable[[EventEnvelope], EventEnvelope],
    ) -> EventEnvelope:
        event = self.verify(envelope, raw_envelope=raw_envelope)
        if self.receipt_store.has_envelope_id(envelope.envelope_id):
            raise EnvelopeReplayError(f"network envelope {envelope.envelope_id} already accepted")
        if envelope.request_id is not None and self.receipt_store.has_request_id(envelope.request_id):
            raise EnvelopeReplayError(f"network request {envelope.request_id} already accepted")

        appended = append_event(event)
        self.receipt_store.record_receipt(
            envelope_id=envelope.envelope_id,
            request_id=envelope.request_id,
            sender_node_id=envelope.sender_node_id,
            message_type=envelope.message_type.value,
            payload_digest=envelope.payload_digest,
        )
        return appended

    def verify(self, envelope: SignedNetworkEnvelope, *, raw_envelope: dict[str, object]) -> EventEnvelope:
        if envelope.message_type is not NetworkMessageType.EVENT_APPEND:
            raise EnvelopeVerificationError("signed ingress only accepts event.append envelopes")
        _verify_common_envelope(
            envelope,
            raw_envelope=raw_envelope,
            trusted_nodes=self.trusted_nodes,
            now_fn=self.now_fn,
            required_capability=NodeCapability.EVENT_APPEND,
        )

        try:
            event = EventEnvelope.model_validate(envelope.payload)
        except ValidationError as exc:
            raise EnvelopeVerificationError("payload is not a valid event envelope") from exc
        return event


class LeaseCommandIngressVerifier:
    def __init__(
        self,
        *,
        trusted_nodes: TrustedNodeRegistry,
        receipt_store: SQLiteNetworkEnvelopeStore,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.trusted_nodes = trusted_nodes
        self.receipt_store = receipt_store
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self.receipt_store.init_schema()

    def verify_and_record(
        self,
        envelope: SignedNetworkEnvelope,
        *,
        raw_envelope: dict[str, object],
        lease_id: str | None = None,
        apply_command: Callable[[LeaseCommand], T],
    ) -> T:
        command = self.verify(envelope, raw_envelope=raw_envelope, lease_id=lease_id)
        if self.receipt_store.has_envelope_id(envelope.envelope_id):
            raise EnvelopeReplayError(f"network envelope {envelope.envelope_id} already accepted")
        if envelope.request_id is not None and self.receipt_store.has_request_id(envelope.request_id):
            raise EnvelopeReplayError(f"network request {envelope.request_id} already accepted")

        result = apply_command(command)
        self.receipt_store.record_receipt(
            envelope_id=envelope.envelope_id,
            request_id=envelope.request_id,
            sender_node_id=envelope.sender_node_id,
            message_type=envelope.message_type.value,
            payload_digest=envelope.payload_digest,
        )
        return result

    def verify(
        self,
        envelope: SignedNetworkEnvelope,
        *,
        raw_envelope: dict[str, object],
        lease_id: str | None = None,
    ) -> LeaseCommand:
        if envelope.message_type not in _LEASE_MESSAGE_CAPABILITIES:
            raise EnvelopeVerificationError("signed lease ingress only accepts lease.* envelopes")

        _verify_common_envelope(
            envelope,
            raw_envelope=raw_envelope,
            trusted_nodes=self.trusted_nodes,
            now_fn=self.now_fn,
            required_capability=_LEASE_MESSAGE_CAPABILITIES[envelope.message_type],
        )

        if not isinstance(envelope.payload, dict):
            raise EnvelopeVerificationError("payload is not a valid lease command")

        action = _LEASE_MESSAGE_ACTIONS[envelope.message_type]
        payload = dict(envelope.payload)
        if payload.get("node_id") != envelope.sender_node_id:
            raise EnvelopeVerificationError("payload node_id must match sender_node_id")
        if envelope.request_id is not None and payload.get("request_id") != envelope.request_id:
            raise EnvelopeVerificationError("payload request_id must match network request_id")
        if lease_id is not None:
            payload_lease_id = payload.get("lease_id")
            if payload_lease_id is not None and payload_lease_id != lease_id:
                raise EnvelopeVerificationError("payload lease_id must match request path")
            payload["lease_id"] = lease_id
        payload["action"] = action.value

        try:
            return LeaseCommand.model_validate(payload)
        except ValidationError as exc:
            raise EnvelopeVerificationError("payload is not a valid lease command") from exc


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_payload_digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _verify_common_envelope(
    envelope: SignedNetworkEnvelope,
    *,
    raw_envelope: dict[str, object],
    trusted_nodes: TrustedNodeRegistry,
    now_fn: Callable[[], datetime],
    required_capability: NodeCapability,
) -> None:
    node = trusted_nodes.get(envelope.sender_node_id)
    if node is None:
        raise EnvelopeVerificationError("sender_node_id is not trusted for signed ingress")
    if required_capability not in node.capabilities:
        raise EnvelopeVerificationError(
            f"sender_node_id is not authorized for {envelope.message_type.value} capability"
        )

    signing_key = next((item for item in node.signing_keys if item.key_id == envelope.sender_key_id), None)
    if signing_key is None:
        raise EnvelopeVerificationError("sender_key_id is not known for trusted sender")
    if signing_key.status is not SigningKeyStatus.ACTIVE:
        raise EnvelopeVerificationError("sender_key_id is not active for trusted sender")
    if signing_key.signature_scheme.value != envelope.signature_scheme.value:
        raise EnvelopeVerificationError("signature_scheme does not match trusted sender key")

    now = now_fn()
    if node.expires_at is not None and node.expires_at < now:
        raise EnvelopeVerificationError("sender_node_id trust document is expired")
    if envelope.expires_at is not None and envelope.expires_at < now:
        raise EnvelopeVerificationError("network envelope is expired")
    if envelope.replay_window_seconds is not None:
        replay_deadline = envelope.sent_at + timedelta(seconds=envelope.replay_window_seconds)
        if replay_deadline < now:
            raise EnvelopeVerificationError("network envelope replay window has expired")

    expected_payload_digest = canonical_payload_digest(raw_envelope.get("payload"))
    if envelope.payload_digest != expected_payload_digest:
        raise EnvelopeVerificationError("payload_digest does not match canonical payload")
    _verify_signature(envelope, raw_envelope=raw_envelope, public_key=signing_key.public_key)


def _verify_signature(
    envelope: SignedNetworkEnvelope,
    *,
    raw_envelope: dict[str, object],
    public_key: str,
) -> None:
    public_key_bytes = _decode_key_material(public_key, field_name="public_key")
    signature_bytes = _decode_key_material(envelope.signature, field_name="signature")
    canonical_envelope = {key: value for key, value in raw_envelope.items() if key != "signature"}
    try:
        verifier = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        verifier.verify(signature_bytes, canonical_json_bytes(canonical_envelope))
    except (InvalidSignature, ValueError) as exc:
        raise EnvelopeVerificationError("signature is invalid for canonical envelope payload") from exc


def _decode_key_material(value: str, *, field_name: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except BinasciiError as exc:
        raise EnvelopeVerificationError(f"{field_name} must be base64 encoded") from exc
