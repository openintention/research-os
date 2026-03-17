# AGENTS.md

## Mission

Build a machine-native research operating system for autonomous AI research workflows.

The product is **not** a code host with PRs.
The product is a control plane with:
- immutable lineage events
- frontier materialization
- planner queries
- adoption / reproduction / contradiction semantics
- publication mirrors for humans

## Read order

1. `spec/product.yaml`
2. `spec/backlog.yaml`
3. `spec/domain-model.yaml`
4. `ARCHITECTURE.md`
5. `docs/adr/*.md`

## Non-negotiables

1. **Control plane and artifact plane stay separate.**
   - Control plane: events, claims, frontiers, subscriptions, leases, planner output.
   - Artifact plane: git refs, checkpoints, logs, weights, datasets, papers.

2. **The source of truth is the event log.**
   - Do not make GitHub state authoritative.
   - Do not make branch tips authoritative.
   - Do not encode semantics only in branch names.

3. **Prefer typed lineage edges over generic text metadata.**
   - `derived_from`
   - `produced`
   - `reproduces`
   - `contradicts`
   - `adopts`
   - `composes`
   - `supersedes`

4. **Planner quality matters more than scheduler cleverness.**
   The central question is what should be tried next, not only where it should run.

5. **APIs are machine-first.**
   Human-facing PRs, discussions, reports, and summaries are generated views.

## Planning and tracking
Linear is the canonical planning system for this repository.
- Team: ANJ
- Context/workstream: OpenIntention
- Use the Linear issue ID (`ANJ-*`) as the canonical task and discussion reference.
- Keep backlog/spec IDs (`OS-*`) as references, not as canonical issue IDs.
- Linear ticket titles should use the plain task name without the backlog ID prefix.
- Linear ticket descriptions should start with:
  `Backlog reference: OS-...`
  `Canonical discussion reference: ANJ-...`
- Before implementation, attach work to an existing Linear issue or create one.
- Keep plans, progress notes, and completion notes in Linear.
- Do not create local planning files unless explicitly asked.
- At the end of each task, post verification results and the next recommended issue in Linear.

## Verification discipline

- Nothing is done until the relevant end-to-end verification for the affected surface has passed.
- Compiling, static review, or "looks good" checks do not count as done.
- Tests alone do not count when the changed surface is hosted, public, worker-facing, or observer-visible.
- Use the smallest applicable verification threshold from `docs/verification-gate.md`, then add any stronger live proof required by the change.
- Do not move a Linear issue to `Done` without posting the verification result that satisfies this bar.

## Coding conventions

- Keep Python 3.11 compatibility.
- Keep functions small and typed.
- Preserve `spec/` and `schemas/` as machine-readable sources of truth.
- Add tests for any new behavior.
- When a design choice changes semantics, add an ADR in `docs/adr/`.

## Current priorities

- materialized projections instead of full-scan projections
- artifact registry and content-addressed references
- planner policies per objective family
- subscription / notification layer
- GitHub publisher
- distributed substrate adapter

## Avoid

- shipping a UI-first repo without solid control-plane semantics
- encoding business logic only in prompts or README text
- assuming a single canonical trunk / merge flow
- adding a message queue before the domain model is stable
