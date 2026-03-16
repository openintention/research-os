# ADR 0011: Heartbeat observations and lease liveness remain coordination state

## Status
Accepted

## Context
The mesh-foundation work now has:
- signed node identity and network envelopes,
- signed `event.append` ingress,
- and signed lease-command ingress.

The next step is node liveness.

Without a first-class heartbeat contract, active leases can only tell us who acquired work, not
whether the holder still looks alive from the control plane.

At the same time, heartbeats must not become a second truth surface for research outcomes:
- they should not enter the immutable lineage event log,
- they should not override claim or frontier semantics,
- and they should not make lease state authoritative over valid late research evidence.

## Decision
Add a dedicated signed heartbeat ingress path and explicit coordination read views.

### Heartbeat ingress
Trusted nodes may submit signed `node.heartbeat` envelopes through a dedicated API path.

The payload is a bounded heartbeat command:
- schema: `openintention-node-heartbeat-v1`
- version: `1`
- request id
- node id
- ttl seconds

The same edge checks used for signed events and signed lease commands apply here:
- trusted sender lookup
- capability check
- canonical payload digest verification
- signature verification
- expiry / replay window validation
- replay rejection through transport receipts

### Storage boundary
Heartbeat observations are stored in coordination storage only.

They remain separate from:
- lineage events
- claims
- frontier state
- publication evidence

The control plane stores the latest observed heartbeat per node and derives freshness from the
stored expiry boundary.

### Lease liveness view
Lease state itself stays unchanged.

Instead, read models may attach liveness context to a lease:
- `healthy`
- `stale`
- `missing`
- `not_applicable`

This liveness view is derived from the lease holder node id and the latest stored heartbeat.
It explains coordination state, but it does not mutate research truth.

## Consequences
- operators and future nodes can inspect whether an active lease holder still appears alive
- late valid lineage can still append even if the lease holder heartbeat went stale
- heartbeat traffic becomes part of the mesh foundation without polluting the event log

## References
- Implementation issue: ANJ-81
- Related ADRs: 0009, 0010
