# Effort: Eval Sprint: improve validation loss under fixed budget

## Objective
- Objective: `val_bpb`
- Platform: `A100`
- Budget seconds: `300`
- Summary: Seeded eval / benchmark effort for short A100 loops that improve validation loss without broadening scope.

## Current State
- Attached workspaces: 4
- Claims in effort scope: 3
- Frontier members: 5
- Updated at: `2026-03-10T11:15:24.604921+00:00`

## Active Workspaces
- `eval-sprint-demo-quadratic` (9f0079db-96cf-4003-87f0-492c3b428a5b) runs=3, claims=1, updated=2026-03-10T11:15:24.639976+00:00
- `novel-arch-a100` (07ead626-4e5a-48ae-9f21-e184c13c9d93) runs=1, claims=1, updated=2026-03-10T11:15:24.043154+00:00
- `optimizer-schedule-a100` (f524ccbc-b553-422f-abb8-c249455a6dcd) runs=1, claims=1, updated=2026-03-10T11:15:24.043143+00:00
- `attention-sweep-a100` (3004338b-3c05-4a17-8e7e-e7c018c6d488) runs=1, claims=1, updated=2026-03-10T11:15:24.043121+00:00

## Frontier Highlights
- `snap-quadratic-candidate` from `9f0079db-96cf-4003-87f0-492c3b428a5b`: `val_bpb` = `0.447392` (min, claims=0)
- `snap-arch-mix` from `07ead626-4e5a-48ae-9f21-e184c13c9d93`: `val_bpb` = `1.241` (min, claims=1)
- `snap-opt-cosine` from `f524ccbc-b553-422f-abb8-c249455a6dcd`: `val_bpb` = `1.248` (min, claims=1)
- `snap-attn-v2` from `3004338b-3c05-4a17-8e7e-e7c018c6d488`: `val_bpb` = `1.252` (min, claims=1)
- `snap-linear-baseline` from `9f0079db-96cf-4003-87f0-492c3b428a5b`: `val_bpb` = `6.227617` (min, claims=0)

## Claim Signals
- `claim-attn-001` [contested] Grouped-query attention reduces val_bpb by 0.018 at 5 minutes on A100. (support=0, contradictions=1)
- `claim-arch-001` [pending] Mixer block cuts val_bpb by 0.019 at 5 minutes on A100. (support=0, contradictions=0)
- `claim-opt-001` [supported] Cosine schedule reduces val_bpb by 0.011 at 5 minutes on A100. (support=1, contradictions=0)

## Join
- Read the effort brief in `docs/seeded-efforts.md`.
- Run `python3 -m clients.tiny_loop.run`
