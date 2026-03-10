# Rama adapter seam

This directory is a landing zone for a future Rama-backed implementation.

## Conceptual mapping

- `events` SQLite table -> one or more Rama depots
- frontier / claim / workspace projections -> PStates
- `recommend_next` -> query topology
- publication pipelines -> stream or microbatch topology
- worker routing -> external workers, plus capability-aware placement if desired

## Suggested first adapter boundary

Implement the same logical interface as `research_os.ledger.protocol.EventStore`:

- append event
- list events (bootstrap / backfill only)
- optionally publish precomputed query results

The service layer and API should not need to know whether the substrate is SQLite,
Postgres, or Rama.

## Recommended PState families

- `workspace_heads`
- `workspace_summaries`
- `frontier_members`
- `claim_summaries`
- `lease_table`
- `subscription_state`

## Recommended query topologies

- `workspace(workspace_id)`
- `frontier(objective, platform, budget_seconds)`
- `claims(objective, platform)`
- `recommend_next(objective, platform, budget_seconds, worker_capabilities)`

## Important design constraint

Keep publication mirrors downstream of control-plane truth.
Do not make GitHub PRs or Discussions the canonical API for agents.
