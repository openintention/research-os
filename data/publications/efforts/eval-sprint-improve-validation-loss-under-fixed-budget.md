# Effort: Eval Sprint: improve validation loss under fixed budget

## Objective
- Objective: `val_bpb`
- Platform: `A100`
- Budget seconds: `300`
- Summary: Seeded eval / benchmark effort for short A100 loops that improve validation loss without broadening scope.

## Lifecycle
- Proof version: `1`
- Proof state: `current`

## Proof Context
- Best current result: `val_bpb` = `0.447392` from `participant-34bd925e` with `1` claim signal.
- Latest claim signal: `participant-34bd925e` left a `supported` claim: Adding the quadratic feature improves the seeded eval objective in this local proxy loop under the fixed budget.
- Latest visible handoff: Left behind 3 runs, 1 claim, and 1 reproduction that the next participant can inspect and continue.

## Current State
- Attached workspaces: 4
- Claims in effort scope: 4
- Frontier members: 5
- Updated at: `2026-03-12T23:02:02.265096+00:00`

## Active Workspaces
- `eval-sprint-demo-quadratic` (55584fb9-ac6d-4a31-8c2c-659d341234cf) actor=participant-34bd925e, role=contributor, window=current, path=proxy, runs=3, claims=1, reproductions=1, updated=2026-03-12T23:02:02.284237+00:00
- `novel-arch-a100` (409cbc5f-994f-4205-870c-2a38ee215921) actor=seed, role=contributor, window=current, path=standard, runs=1, claims=1, reproductions=0, updated=2026-03-12T23:02:01.779618+00:00
- `optimizer-schedule-a100` (8c463b3b-fded-4560-b98d-84c0b0bfca3e) actor=seed, role=contributor, window=current, path=standard, runs=1, claims=1, reproductions=0, updated=2026-03-12T23:02:01.779613+00:00
- `attention-sweep-a100` (4dab12b9-b1ef-4932-a123-ca46ec3496b0) actor=seed, role=contributor, window=current, path=standard, runs=1, claims=1, reproductions=1, updated=2026-03-12T23:02:01.778968+00:00

## Frontier Highlights
- `55584fb9-snap-quadratic-candidate` from `participant-34bd925e` (`55584fb9-ac6d-4a31-8c2c-659d341234cf`): `val_bpb` = `0.447392` (min, claims=1)
- `snap-arch-mix` from `seed` (`409cbc5f-994f-4205-870c-2a38ee215921`): `val_bpb` = `1.241` (min, claims=1)
- `snap-opt-cosine` from `seed` (`8c463b3b-fded-4560-b98d-84c0b0bfca3e`): `val_bpb` = `1.248` (min, claims=1)
- `snap-attn-v2` from `seed` (`4dab12b9-b1ef-4932-a123-ca46ec3496b0`): `val_bpb` = `1.252` (min, claims=1)
- `55584fb9-snap-linear-baseline` from `participant-34bd925e` (`55584fb9-ac6d-4a31-8c2c-659d341234cf`): `val_bpb` = `6.227617` (min, claims=0)

## Claim Signals
- `55584fb9-claim-quadratic-001` from `participant-34bd925e` [supported] Adding the quadratic feature improves the seeded eval objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)
- `claim-attn-001` from `seed` [contested] Grouped-query attention reduces val_bpb by 0.018 at 5 minutes on A100. (support=0, contradictions=1)
- `claim-arch-001` from `seed` [pending] Mixer block cuts val_bpb by 0.019 at 5 minutes on A100. (support=0, contradictions=0)
- `claim-opt-001` from `seed` [supported] Cosine schedule reduces val_bpb by 0.011 at 5 minutes on A100. (support=1, contradictions=0)

## Join
- Read the effort brief in `docs/seeded-efforts.md`.
- Optional: add `--actor-id <handle>` to make lightweight participant attribution visible.
- Run `python3 -m clients.tiny_loop.run`
