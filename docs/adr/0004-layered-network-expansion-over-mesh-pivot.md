# ADR 0004: Layered network expansion over a mesh pivot

## Status
Accepted

## Context
`research-os` already has the core shape of a machine-native research control plane:
- an immutable event log as the source of truth
- typed lineage semantics for runs, claims, contradictions, reproductions, adoptions, and summaries
- materialized frontier and claim projections
- artifact references kept separate from control-plane state
- planner recommendations derived from lineage and frontier state
- publication mirrors generated from machine state
- seeded shared efforts and a thin external client loop that uses the HTTP API end to end

At the same time, the product direction is broader than a local single-node tool. The repo
strategy already points toward a collaborative research network with seeded shared efforts,
bounded participation, and later broader objective creation.

There is now a temptation to pivot the product toward a node-based mesh network because that
direction is legible in the market. However, a full pivot would currently outrun what the
system actually provides. Today the product does **not** have:
- a live peer mesh
- gossip or sync protocols
- cryptographic node identities
- verifier/challenge/dispute loops
- a public network explorer with live multi-party state

This creates a strategic fork:
- pivot hard into network mechanics and compete on mesh features
- stay purely control-plane-first and defer all network behavior
- or grow network behavior on top of the current control plane in stages

## Decision
Expand toward a research network in **layers on top of the current control plane**.

Do **not** pivot `research-os` into a mesh-first product now.

Do **not** market the current system as if it already has live network properties that do not
exist.

The product direction can be described publicly as a research network in the making, but the
implementation sequence remains:
1. shared efforts and real multi-party participation on a hosted/shared control plane
2. stronger planner loops and effort-level explorer views
3. bounded remote contributor and verifier roles
4. only then node identity, signed events, and richer network mechanics

`research-os` remains the machine-native control plane underneath that evolution.

## Rationale
This preserves the repo's strongest differentiators:
- typed research semantics over generic job metadata
- event-sourced evidence rather than branch-centric history
- adoption/reproduction/contradiction as first-class primitives
- frontier state keyed by objective, platform, and budget
- planner quality as the center of coordination value

A mesh-first pivot would force the next product cycle to compete on:
- transport and peer sync
- node ops and liveness
- identity and signing
- artifact transfer
- explorer polish

Those are valuable later, but they are not where `research-os` is currently strongest.

## Consequences

### What to build next
- real shared participation on top of a hosted/shared control plane
- effort-level explorer views derived from control-plane state
- planner behavior that improves the quality of shared efforts
- role concepts such as contributor and verifier before a full node mesh

### What to defer
- peer-to-peer gossip
- generalized mesh sync
- live node marketplace framing
- dispute/reputation systems before real abuse pressure exists
- explorer theater that implies a live network before one exists

### Public positioning
- it is valid to describe the product direction as a research network
- it is not valid to imply that a live mesh already exists
- the public message should lead with shared objectives, lineage, evidence, frontier state,
  and planner guidance rather than with nodes or decentralization

## Non-goals
This decision does **not** reject future network capabilities.

It rejects doing them out of sequence, before the shared-effort and planner-centered value of
the system is clearly stronger than a generic experiment mesh.
