# Architecture

## Product shape

This repo starts from one core bet:

> autonomous research needs machine-native lineage management more than it needs a human-centric branch and merge workflow.

The system is split into two planes.

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
- Rama depots + PStates + query topologies

## Rama mapping

The future Rama path is:

- event log -> Rama depot(s)
- projections -> PStates
- planner queries -> query topologies
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

That is enough to support:
- local agents
- external workers
- publishers that mirror findings into GitHub
- future websockets or subscriptions

## Near-term extension path

1. Materialize projections into tables instead of scanning the event log.
2. Add content-addressed artifact registry.
3. Add subscriptions and notification fan-out.
4. Add GitHub publisher that emits PR-like and Discussion-like views.
5. Add lease tables and worker heartbeats.
6. Add a Rama-backed adapter with the same logical interface.
