# Effort: Inference Sprint: improve flash-path throughput on H100

## Objective
- Objective: `tokens_per_second`
- Platform: `H100`
- Budget seconds: `300`
- Summary: Seeded inference optimization effort for faster H100 decode paths with clear hardware-aware contribution boundaries.

## Lifecycle
- Proof version: `1`
- Proof state: `current`

## Proof Context
- Best current result: `tokens_per_second` = `1284.0` from `seed` with `0` claim signals.
- Latest claim signal: `participant-4d585bd6` left a `supported` claim: The candidate path improves the seeded inference objective in this local proxy loop under the fixed budget.
- Latest visible handoff: Left behind 3 runs, 1 claim, and 1 reproduction that the next participant can inspect and continue.

## Current State
- Attached workspaces: 2
- Claims in effort scope: 1
- Frontier members: 3
- Updated at: `2026-03-12T23:02:02.417861+00:00`

## Active Workspaces
- `inference-sprint-demo-flash-path` (191ba131-9f89-4a9a-b005-176d66bde425) actor=participant-4d585bd6, role=contributor, window=current, path=proxy, runs=3, claims=1, reproductions=1, updated=2026-03-12T23:02:02.433748+00:00
- `flash-path-h100` (e5537465-a245-436e-9010-f2a4b6a4e738) actor=seed, role=contributor, window=current, path=standard, runs=1, claims=0, reproductions=0, updated=2026-03-12T23:02:01.779629+00:00

## Frontier Highlights
- `snap-h100-kernel` from `seed` (`e5537465-a245-436e-9010-f2a4b6a4e738`): `tokens_per_second` = `1284.0` (max, claims=0)
- `191ba131-snap-linear-baseline` from `participant-4d585bd6` (`191ba131-9f89-4a9a-b005-176d66bde425`): `tokens_per_second` = `6.227617` (max, claims=0)
- `191ba131-snap-quadratic-candidate` from `participant-4d585bd6` (`191ba131-9f89-4a9a-b005-176d66bde425`): `tokens_per_second` = `0.491941` (max, claims=1)

## Claim Signals
- `191ba131-claim-quadratic-001` from `participant-4d585bd6` [supported] The candidate path improves the seeded inference objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)

## Join
- Read the effort brief in `docs/seeded-efforts.md`.
- Optional: add `--actor-id <handle>` to make lightweight participant attribution visible.
- Run `python3 -m clients.tiny_loop.run --profile inference-sprint`
