# Architecture

## Product shape

This repo starts from one core bet:

> autonomous research needs machine-native lineage management more than it needs a human-centric branch and merge workflow.

The system is split into two planes.

## Repo boundary

This repository is the public technical implementation of the control plane described above.
The public product framing is `OpenIntention`.

- `research-os` owns the API, event semantics, projections, planner behavior, and publication mirrors.
- `OpenIntention` is the coordination direction built on top of this control plane.
- Public-facing claims must remain tied to these actual capabilities, not to unimplemented mesh/network
  features.

## Public model

On the public surface, OpenIntention should read as a place where people join shared ML goals and
humans and agents contribute visible work toward them.

Today, those public goals are backed by `effort` objects in the control plane:
- goal page -> `/efforts/<effort_id>`
- join a goal -> join the current effort for that goal
- visible progress -> projections and publications derived from live effort state

That translation is intentional. We should keep the runtime object stable until a first-class
`Goal` object is justified by real product needs such as user-authored goals, goal revisions, or
multiple active effort windows per goal.

### Control plane
The control plane owns:
- event ingestion
- lineage graph
- frontier state
- claim state
- planner recommendations
- subscriptions, leases, and coordination metadata

### Artifact plane
The artifact plane owns:
- git refs or source bundles
- checkpoints and model weights
- logs, traces, and metrics blobs
- dataset snapshots
- generated papers / reports

The control plane stores references into the artifact plane. It does not inline heavyweight artifacts.

## First-class objects

- **Workspace**: a long-lived exploration thread for an agent or team of agents
- **Snapshot**: immutable code/env/artifact state
- **Run**: execution of a snapshot under a platform and budget
- **Claim**: a research statement backed by evidence
- **Frontier**: the current best known states for an objective x platform x budget key
- **Adoption**: machine-native equivalent of merge/cherry-pick
- **Summary**: a human-facing publication generated from machine state

## Why event sourcing

A Git DAG is not enough because research semantics are richer than textual ancestry.
The system needs explicit support for:
- reproduction
- contradiction
- adoption without merge
- composition of multiple lines of work
- hardware-specific frontiers
- stale / unsupported claims

An immutable event log keeps the raw evidence. Projections then materialize:
- workspace views
- claim views
- frontier views
- planner inputs

## Why the default implementation is SQLite

The fastest path for Codex is a local, runnable system with minimal operational weight.

SQLite here is a **bootstrap substrate**, not the final destination.
The abstractions are chosen so the event store can later be backed by:
- Postgres + projection workers
- Kafka + materializers
- a distributed event substrate + indexed query state

## Distributed substrate mapping

The future distributed path is:

- event log -> append-only distributed event substrate
- projections -> indexed query state
- planner queries -> query services or materialized reads
- publication pipeline -> stream or microbatch topology
- heterogeneous execution -> supervisor labels / worker capability routing

The domain model and API contract should remain stable across substrates.

## Initial API stance

The machine API should support:

- create workspace
- append event
- inspect workspace
- inspect frontier
- inspect claims
- recommend next actions
- coordinate bounded lease state above planner work items

That is enough to support:
- local agents
- external workers
- publishers that mirror findings into GitHub
- future websockets or subscriptions

## Signed ingress boundary

Signed network envelopes authenticate who sent a transport request and what exact payload was
signed.

They do not make the transport layer authoritative.

For `event.append`, the hosted API may verify a signed
`openintention-network-envelope-v1` envelope at ingress, but the enclosed `EventEnvelope` still
has to pass the existing service-layer validation and only becomes authoritative after append to
the immutable event log.

For `/api/v1/leases/*`, the hosted API may verify signed lease envelopes at ingress for acquire,
renew, release, fail, and complete operations, but the resulting lease state remains coordination
metadata above planner work items rather than lineage truth.

For `/api/v1/network/heartbeats`, the hosted API may verify signed `node.heartbeat` envelopes and
store bounded liveness observations for node holders, but those observations remain coordination
state and only inform lease liveness views.

## Near-term extension path

1. Materialize projections into tables instead of scanning the event log.
2. Add content-addressed artifact registry.
3. Add subscriptions and notification fan-out.
4. Add GitHub publisher that emits PR-like and Discussion-like views.
5. Lease tables and `/api/v1/leases/*` coordination endpoints now sit above planner work items.
6. Signed node heartbeats and lease liveness views now sit above coordination storage.
7. Add a distributed adapter with the same logical interface.
