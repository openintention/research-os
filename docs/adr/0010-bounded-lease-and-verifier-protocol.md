# ADR 0010: Bounded lease and verifier protocol above the API control plane

## Status
Accepted

## Context
If OpenIntention expands from a hosted network into a real node-aware coordination layer, work
pickup cannot rely on loose polling alone.

However, the lease layer must not become a hidden scheduler that overrides planner semantics or a
new authority surface that competes with the event log.

The core constraints remain:
- the planner decides what work is worth doing,
- the event log remains the source of truth for research outcomes,
- verifier behavior must be explicit and inspectable,
- duplicate or late work should remain understandable rather than silently discarded.

## Decision
Define bounded leases as **coordination metadata** over planner-scoped work items.

The lease protocol sits above the existing hosted API control plane.
It coordinates who is currently attempting a work item, but it does not decide whether research
evidence is true.

### Lease object
The first contract uses:
- schema: `openintention-lease-v1`
- version: `1`
- work item type
- participant role
- target subject
- planner fingerprint
- bounded duration
- current holder node
- current status

Work item types for the first protocol:
- `reproduce_claim`
- `contradict_claim`
- `adopt_snapshot`
- `compose_frontier`
- `explore_effort`
- `publish_summary`

### Lease lifecycle
The canonical state machine is:

`available -> acquired -> renewed* -> completed | released | failed | expired`

Rules:
- acquire requires a planner fingerprint or an explicit subject reference,
- renew is only valid for the current holder before expiry,
- release is voluntary and leaves the work item available again,
- fail records bounded failure metadata and frees the work item for others,
- expire happens deterministically when the TTL elapses without renewal,
- complete records coordination completion only after the worker has already published the
  corresponding research evidence or summary payload.

### Planner boundary
Leases bind to planner output, not to an opaque queue.

The planner fingerprint is the stable reference to:
- action type,
- target claim/snapshot/effort,
- objective/platform/budget context,
- and recommendation generation context.

This keeps planner quality central and avoids turning leases into a generic job queue without
research semantics.

### Verifier protocol
Verifier work is a first-class lease mode, not an afterthought.

Rules:
- verifier leases must use `participant_role=verifier`,
- verifier work should normally target an explicit claim or contradiction opportunity,
- verifier completion does **not** directly flip claim state,
- verifier completion only becomes meaningful once the verifier has appended ordinary lineage
  events such as `claim.reproduced` or `claim.contradicted` from a verifier workspace.

This preserves the event log as the place where support or contradiction actually exists.

### Idempotency and replay
Lease commands use:
- schema: `openintention-lease-command-v1`
- version: `1`
- caller `request_id`
- caller `node_id`
- optional `lease_id`
- bounded TTL request

Rules:
- repeated `acquire` with the same `request_id` should return the same live lease when possible,
- repeated `renew`, `release`, `fail`, and `complete` commands must be idempotent,
- expired leases cannot be renewed,
- completion for an already expired lease may be recorded as stale coordination metadata but must
  not block valid late lineage events from entering the event log if they still satisfy ingress
  validation.

### Late or duplicate results
The system should prefer preserving evidence over enforcing scheduler purity.

If two workers race the same task:
- both may still append valid research evidence,
- the lease layer explains the duplication,
- the planner and claim/frontier projections decide what that evidence means.

This is especially important for verifier work, where multiple reproductions can still be useful.

## First API shape
The later implementation should expose lease endpoints separately from `/api/v1/events`, for example:
- `POST /api/v1/leases/acquire`
- `POST /api/v1/leases/{lease_id}/renew`
- `POST /api/v1/leases/{lease_id}/release`
- `POST /api/v1/leases/{lease_id}/fail`
- `POST /api/v1/leases/{lease_id}/complete`

These endpoints may accept signed network envelopes at the edge, but the resulting lease state is
still a control-plane projection/table, not a lineage event stream.

## Out of scope
Not part of the first lease protocol:
- stake, slashing, or reputation,
- peer-to-peer gossip,
- challenge courts or dispute resolution,
- distributed artifact transfer,
- consensus on claim truth,
- automatic rejection of valid late research evidence solely because a lease expired.

## Consequences
- later mesh work gets an implementation-ready state machine instead of ad hoc polling behavior,
- verifier work becomes explicit without making verifier state authoritative by itself,
- the current hosted API control plane stays central because leases coordinate work around planner
  outputs and lineage events instead of replacing them.

## References
- Backlog reference: OS-041
- Related issue: ANJ-75
- Implementation issue: ANJ-76
