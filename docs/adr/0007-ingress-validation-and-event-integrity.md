# ADR 0007: Ingress validation for event integrity

## Status
Accepted

## Context
`POST /api/v1/events` accepts external event envelopes from untrusted callers.
As adoption grows, silent ingestion of malformed events would:
- corrupt projections,
- break planner expectations,
- and make contribution quality difficult to reason about.

Recent work on external participatory loops also assumes clear failure signals when
payloads are malformed.

## Decision
Validate incoming events at the service layer before persistence and fail fast on
invalid event shape.

Behavior changes:
- strict per-kind validation for active event kinds (`workspace.started`, `snapshot.published`,
  `run.completed`, `claim.asserted`, `claim.reproduced`, `claim.contradicted`,
  `adoption.recorded`, `summary.published`, `effort.rolled_over`),
- required workspace consistency checks for workspace-scoped events,
- identifier, enum, and bounded-length checks for key payload fields,
- artifact URI/digest and manifest attestation hygiene checks for snapshot and claim references:
  - optional manifest URI/digest/signature fields are validated when present,
  - manifest digests require strict `sha256:<64_hex>` format,
  - manifest URI-to-digest consistency is enforced when digest is an artifact URI,
  - claim manifest provenance is checked against source snapshot provenance when provided,
- duplicate `event_id` rejection mapped to HTTP 409.

The API translates invalid payload errors to HTTP 400 so clients can fix behavior at the
call site instead of corrupting event state.

## Consequences
- invalid events no longer poison event logs, frontier, or claim projections,
- malformed payloads get deterministic errors instead of silent acceptance,
- external clients can depend on explicit status codes and retry with corrected payloads,
- the validation policy becomes part of the documented contract for contributing to the
  control plane.

## References
- Backlog reference: OS-007
- Implementation issue: ANJ-65, ANJ-66
