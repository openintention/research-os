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
- Updated at: `2026-03-10T09:03:34.339608+00:00`

## Active Workspaces
- `eval-sprint-demo-quadratic` (e47e8598-14b7-4bca-80b8-44542cc119d7) runs=3, claims=1, updated=2026-03-10T09:03:34.356487+00:00
- `novel-arch-a100` (10c500d5-cbc1-4fd8-a662-677f693ebf71) runs=1, claims=1, updated=2026-03-10T09:03:33.909562+00:00
- `optimizer-schedule-a100` (eb6c1850-9f76-4208-b332-7757d663fa14) runs=1, claims=1, updated=2026-03-10T09:03:33.909552+00:00
- `attention-sweep-a100` (e839439d-2f49-4efc-beb0-e946e882a79b) runs=1, claims=1, updated=2026-03-10T09:03:33.909526+00:00

## Frontier Highlights
- `snap-quadratic-candidate` from `e47e8598-14b7-4bca-80b8-44542cc119d7`: `val_bpb` = `0.447392` (min, claims=0)
- `snap-arch-mix` from `10c500d5-cbc1-4fd8-a662-677f693ebf71`: `val_bpb` = `1.241` (min, claims=1)
- `snap-opt-cosine` from `eb6c1850-9f76-4208-b332-7757d663fa14`: `val_bpb` = `1.248` (min, claims=1)
- `snap-attn-v2` from `e839439d-2f49-4efc-beb0-e946e882a79b`: `val_bpb` = `1.252` (min, claims=1)
- `snap-linear-baseline` from `e47e8598-14b7-4bca-80b8-44542cc119d7`: `val_bpb` = `6.227617` (min, claims=0)

## Claim Signals
- `claim-attn-001` [contested] Grouped-query attention reduces val_bpb by 0.018 at 5 minutes on A100. (support=0, contradictions=1)
- `claim-arch-001` [pending] Mixer block cuts val_bpb by 0.019 at 5 minutes on A100. (support=0, contradictions=0)
- `claim-opt-001` [supported] Cosine schedule reduces val_bpb by 0.011 at 5 minutes on A100. (support=1, contradictions=0)

## Join
- Read the effort brief in `/Users/aliargun/Documents/GitHub/research-os/docs/seeded-efforts.md`.
- Run `python -m clients.tiny_loop.run`
