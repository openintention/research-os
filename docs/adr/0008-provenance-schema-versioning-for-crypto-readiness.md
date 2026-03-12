# ADR 0008: Provenance schema and version fields for cryptographic readiness

## Status
Accepted

## Context
`ANJ-66` added manifest provenance validation for snapshot and claim events:
- optional manifest URI
- strict digest validation
- optional signature presence checks

This is a necessary safety layer, but it still lacked explicit metadata schema signaling.
Without explicit provenance schema/version metadata, future cryptographic workflows cannot
reliably negotiate signature formats, digest semantics, or verification rules across different
clients and contributors.

## Decision
Add explicit, optional provenance metadata fields to the existing manifest attestation surface:

- `source_bundle_manifest_provenance_schema`
- `source_bundle_manifest_provenance_version`
- `source_bundle_manifest_signature_scheme`
- `candidate_snapshot_manifest_provenance_schema`
- `candidate_snapshot_manifest_provenance_version`
- `candidate_snapshot_manifest_signature_scheme`

Validation rules:
- legacy provenance payloads without new fields remain accepted in this release;
- when any provenance metadata is present, the schema/version pair must both be present;
- provenance version must match an integer version format and be in supported set;
- signature scheme is required when a signature is provided in metadata mode.

Canonical schema constants for this release:

- `openintention-artifact-manifest-v1`
- version: `1`

The chosen naming keeps new clients explicit while preserving backwards compatibility for
existing clients that already submit provenance fields without schema/version.

## Consequences
- API contracts are now explicit enough for later signature verification rollups and verifier tooling.
- New provenance payloads can be validated deterministically for schema and version compatibility.
- Existing clients from ANJ-66-compatible flows remain functional without breaking rollout.
- Future verification work can evolve by introducing a new schema/version pair instead of
retrofitting legacy field meaning.

## References
- Backlog reference: OS-007
- Implementation issue: ANJ-66, ANJ-67
