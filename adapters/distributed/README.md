# Distributed adapter seam

This directory is a landing zone for a future distributed implementation.

## Conceptual mapping

- `events` SQLite table -> one or more immutable event partitions
- frontier / claim / workspace projections -> indexed materialized views
- `recommend_next` -> query service
- publication pipelines -> stream or microbatch processors
- worker routing -> external workers, plus capability-aware placement if desired

## Suggested first adapter boundary

Implement the same logical interface as `research_os.ledger.protocol.EventStore`:

- append event
- list events (bootstrap / backfill only)
- optionally publish precomputed query results

The service layer and API should not need to know whether the substrate is SQLite,
Postgres, or a distributed control-plane backend.

## Recommended indexed state families

- `workspace_heads`
- `workspace_summaries`
- `frontier_members`
- `claim_summaries`
- `lease_table`
- `subscription_state`

## Recommended query surfaces

- `workspace(workspace_id)`
- `frontier(objective, platform, budget_seconds)`
- `claims(objective, platform)`
- `recommend_next(objective, platform, budget_seconds, worker_capabilities)`

## Important design constraint

Keep publication mirrors downstream of control-plane truth.
Do not make GitHub PRs or Discussions the canonical API for agents.
