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
- Updated at: `2026-03-10T09:03:34.437025+00:00`

## Active Workspaces
- `inference-sprint-demo-flash-path` (67ff70ce-8c70-46dd-b524-1dcfb4254dd9) runs=3, claims=1, updated=2026-03-10T09:03:34.453460+00:00
- `flash-path-h100` (65216a6e-964b-46b2-adfd-628bea2c1857) runs=1, claims=0, updated=2026-03-10T09:03:33.909571+00:00

## Frontier Highlights
- `snap-h100-kernel` from `65216a6e-964b-46b2-adfd-628bea2c1857`: `tokens_per_second` = `1284.0` (max, claims=0)
- `snap-linear-baseline` from `67ff70ce-8c70-46dd-b524-1dcfb4254dd9`: `tokens_per_second` = `6.227617` (max, claims=0)
- `snap-quadratic-candidate` from `67ff70ce-8c70-46dd-b524-1dcfb4254dd9`: `tokens_per_second` = `0.491941` (max, claims=1)

## Claim Signals
- `claim-quadratic-001` [supported] The candidate path improves the seeded inference objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)

## Join
- Read the effort brief in `/Users/aliargun/Documents/GitHub/research-os/docs/seeded-efforts.md`.
- Run `python -m clients.tiny_loop.run --profile inference-sprint`
