# Effort: Eval Sprint: improve validation loss under fixed budget

## Objective
- Objective: `val_bpb`
- Platform: `A100`
- Budget seconds: `300`
- Summary: Seeded eval / benchmark effort for short A100 loops that improve validation loss without broadening scope.

## Current State
- Attached workspaces: 3
- Claims in effort scope: 3
- Frontier members: 3
- Updated at: `2026-03-10T08:47:07.541753+00:00`

## Active Workspaces
- `novel-arch-a100` (b736f750-7f8f-4155-a482-70946eb3fda8) runs=1, claims=1, updated=2026-03-10T08:47:07.542900+00:00
- `optimizer-schedule-a100` (1aac0096-a15d-4529-816b-537413c0effe) runs=1, claims=1, updated=2026-03-10T08:47:07.542890+00:00
- `attention-sweep-a100` (b36122f0-eaee-464f-a1a3-5450f30f5948) runs=1, claims=1, updated=2026-03-10T08:47:07.542870+00:00

## Frontier Highlights
- `snap-arch-mix` from `b736f750-7f8f-4155-a482-70946eb3fda8`: `val_bpb` = `1.241` (min, claims=1)
- `snap-opt-cosine` from `1aac0096-a15d-4529-816b-537413c0effe`: `val_bpb` = `1.248` (min, claims=1)
- `snap-attn-v2` from `b36122f0-eaee-464f-a1a3-5450f30f5948`: `val_bpb` = `1.252` (min, claims=1)

## Claim Signals
- `claim-attn-001` [contested] Grouped-query attention reduces val_bpb by 0.018 at 5 minutes on A100. (support=0, contradictions=1)
- `claim-arch-001` [pending] Mixer block cuts val_bpb by 0.019 at 5 minutes on A100. (support=0, contradictions=0)
- `claim-opt-001` [supported] Cosine schedule reduces val_bpb by 0.011 at 5 minutes on A100. (support=1, contradictions=0)

## Join
- Read the effort brief in `/Users/aliargun/Documents/GitHub/research-os/docs/seeded-efforts.md`.
- Run `python -m clients.tiny_loop.run`
