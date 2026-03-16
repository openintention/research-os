# ADR 0009: Node identity and signed network envelopes

## Status
Accepted

## Context
The hosted control plane now has a trust floor for incoming event payloads and provenance metadata,
but mesh-oriented coordination still lacks a transport-level identity contract.

Without a first-class node identity and signed envelope format, future node-to-node flows would
have to invent ad hoc sender metadata for:
- event append requests,
- lease acquisition and renewal,
- verifier participation,
- and future sync or heartbeat traffic.

That would create two risks:
- transport identity would drift from the existing event and provenance model,
- or the transport layer would start acting like a second source of truth beside the event log.

## Decision
Define two machine-readable contracts for future mesh foundations:

1. `NodeIdentity`
2. `SignedNetworkEnvelope`

These contracts authenticate who sent a message and what exact payload was signed.
They do **not** replace the event log as research authority.

### Node identity v1
The first mesh pilot uses a small, explicit identity document:

- schema: `openintention-node-identity-v1`
- version: `1`
- one stable `node_id`
- one or more signing keys
- a bounded capability set
- optional transport hints

Requirements:
- first pilot signing scheme is `ed25519` only,
- each envelope must reference the sender `node_id` and `key_id`,
- `node_id` should be a stable identifier derived from the active signing identity,
- capabilities are advisory routing hints, not authorization by themselves.

### Signed network envelope v1
The first mesh pilot uses one transport envelope:

- schema: `openintention-network-envelope-v1`
- version: `1`
- sender node + sender key reference
- message type
- payload schema + payload digest
- signed payload body
- request/replay metadata

Supported message types for the first contract:
- `event.append`
- `lease.acquire`
- `lease.renew`
- `lease.release`
- `lease.fail`
- `lease.complete`
- `node.heartbeat`

Signature rule:
- the implementation should sign the canonical JSON form of the envelope excluding the `signature`
  field itself,
- the canonicalization method for implementation should be RFC 8785 JSON Canonicalization Scheme,
  or an equivalent deterministic serializer agreed by both sides,
- the signed content must include `payload_digest`, `message_type`, sender references, and timing
  metadata so the digest cannot be replayed under a different transport claim.

### Authority boundary
The envelope authenticates transport and payload integrity.

It does **not** make the enclosed payload authoritative research state.

For `event.append`, the enclosed event must still pass the current service-layer validation and only
becomes authoritative after successful append to the event log.

For lease and heartbeat traffic, the envelope authenticates the caller and request, while the
control plane stores the resulting coordination state separately from lineage events.

## First pilot requirements
Required now:
- one node identity schema,
- one signed envelope schema,
- `ed25519` only,
- payload digests in `sha256:<hex>` form,
- replay window metadata,
- request identifiers for idempotent API handling,
- manual trust configuration or operator allowlisting.

Deferred:
- key rotation workflow,
- revocation lists,
- multi-signature envelopes,
- transport encryption policy,
- federated trust roots,
- reputation or stake systems.

## Consequences
- future mesh work can add authenticated transport without inventing a second semantics layer,
- `ANJ-76` and later lease/sync work can reference one common sender contract,
- the current hosted API remains compatible because it can accept these envelopes at the edge while
  still appending ordinary validated events internally.

## References
- Implementation issue: ANJ-75
- Related issue: ANJ-76
