# Effort: Inference Sprint: improve flash-path throughput on H100

## Objective
- Objective: `tokens_per_second`
- Platform: `H100`
- Budget seconds: `300`
- Summary: Seeded inference optimization effort for faster H100 decode paths with clear hardware-aware contribution boundaries.

## Current State
- Attached workspaces: 2
- Claims in effort scope: 1
- Frontier members: 3
- Updated at: `2026-03-10T11:15:24.760107+00:00`

## Active Workspaces
- `inference-sprint-demo-flash-path` (7b62fe30-da89-41ac-9760-050e347ee80a) runs=3, claims=1, updated=2026-03-10T11:15:24.787517+00:00
- `flash-path-h100` (a89e3196-580c-4413-8194-bc5f94cdcb1c) runs=1, claims=0, updated=2026-03-10T11:15:24.043162+00:00

## Frontier Highlights
- `snap-h100-kernel` from `a89e3196-580c-4413-8194-bc5f94cdcb1c`: `tokens_per_second` = `1284.0` (max, claims=0)
- `snap-linear-baseline` from `7b62fe30-da89-41ac-9760-050e347ee80a`: `tokens_per_second` = `6.227617` (max, claims=0)
- `snap-quadratic-candidate` from `7b62fe30-da89-41ac-9760-050e347ee80a`: `tokens_per_second` = `0.491941` (max, claims=1)

## Claim Signals
- `claim-quadratic-001` [supported] The candidate path improves the seeded inference objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)

## Join
- Read the effort brief in `docs/seeded-efforts.md`.
- Run `python3 -m clients.tiny_loop.run --profile inference-sprint`
