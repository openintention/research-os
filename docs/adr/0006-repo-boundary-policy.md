# ADR 0006: Repo boundary policy and remote-branch hygiene

## Status
Accepted

## Context

`research-os` has grown into both a technical control-plane implementation and a highly visible
product entry point. At the same time, we want a clean public story for OpenIntention while keeping
space for internal experimentation.

Recent work has shown that without a hard boundary, public docs can accidentally expose unfinished
architecture details or drift from what can actually be run today.

## Decision

`research-os` remains the canonical technical repository for:

- event log model and API contract
- materialized projections
- planner semantics
- artifact reference model
- published effort/workspace snapshots and reproducible smoke commands
- launch scripts and tests required for contribution

`OpenIntention` is the public brand and user-facing direction on top of this control plane.
It is explicitly a product framing, not the same thing as a full node/network product.

## Boundary Rules

Public-facing documentation in this repo must:

- describe machine-first behavior and verified behavior paths
- avoid speculative implementation details (e.g. non-existent modules or premature mesh/network claims)
- keep terminology aligned with this repo’s event, frontier, claim, workspace, and planner model

Internal or experimental work must be gated until it is represented through the control-plane primitives
that the event log and API actually expose.

## Branch Hygiene Rule

- `codex/anj-*` branches are ephemeral implementation branches.
- After merge into `main`, these branches should be removed from the public remote to preserve repo
  discoverability.
- The public repo should not retain dozens of stale integration branches as a long-lived surface.

## Consequences

1. Public announcements and onboarding copy must remain in terms of `OpenIntention` + `research-os` as
   control plane.
2. New experimentation should be staged through existing public primitives and removed from this repo
   once it is superseded by a concrete control-plane capability.
3. Merges that close branch-based experiments should be followed by explicit remote cleanup.

