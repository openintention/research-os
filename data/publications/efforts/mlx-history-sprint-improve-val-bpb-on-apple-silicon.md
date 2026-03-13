# Effort: MLX History Sprint: improve val_bpb on Apple Silicon

## Objective
- Objective: `val_bpb`
- Platform: `Apple-Silicon-MLX`
- Budget seconds: `300`
- Summary: Shared MLX history effort for compounding Apple Silicon val_bpb improvements through adoption, continuation, and visible frontier progress.

## Lifecycle
- Proof version: `1`
- Proof state: `current`

## Proof Context
- Best current result: `val_bpb` = `1.807902` from `worker-smoke` with `1` claim signal.
- Latest claim signal: `worker-smoke` left a `pending` claim: `reduce depth from 8 to 4` improved val_bpb from 2.533728 to 1.807902 on MLX history.
- Latest visible handoff: Left behind 1 run, 1 claim, and 1 adoption that the next participant can inspect and continue.

## Current State
- Attached workspaces: 2
- Claims in effort scope: 2
- Frontier members: 2
- Updated at: `2026-03-13T07:03:12.605800+00:00`

## Active Workspaces
- `mlx-history-worker-5efc7aa` (5000f39c-4e6c-4d32-9137-792f4be0b34a) actor=worker-smoke, role=contributor, window=current, path=external-harness:mlx-history:overnight-autoresearch, runs=1, claims=1, reproductions=0, updated=2026-03-13T07:03:12.618654+00:00
- `mlx-history-worker-4161af3` (c7d66905-f6b1-4e7f-b8da-6242404346d4) actor=worker-smoke, role=contributor, window=current, path=external-harness:mlx-history:overnight-autoresearch, runs=1, claims=1, reproductions=0, updated=2026-03-13T07:03:12.565585+00:00

## Frontier Highlights
- `5000f39c-snap-5efc7aa` from `worker-smoke` (`5000f39c-4e6c-4d32-9137-792f4be0b34a`): `val_bpb` = `1.807902` (min, claims=1)
- `c7d66905-snap-4161af3` from `worker-smoke` (`c7d66905-f6b1-4e7f-b8da-6242404346d4`): `val_bpb` = `2.533728` (min, claims=1)

## Claim Signals
- `5000f39c-claim-5efc7aa` from `worker-smoke` [pending] `reduce depth from 8 to 4` improved val_bpb from 2.533728 to 1.807902 on MLX history. (support=0, contradictions=0)
- `c7d66905-claim-4161af3` from `worker-smoke` [pending] `increase matrix LR to 0.04` improved val_bpb from 2.667000 to 2.533728 on MLX history. (support=0, contradictions=0)

## Join
- Read the effort brief in `README.md#real-overnight-autoresearch-worker`.
- Optional: add `--actor-id <handle>` to make lightweight participant attribution visible.
- Run `python3 scripts/run_overnight_autoresearch_worker.py --repo-path <path_to_mlx_history> --runner-command '<external_harness_command>'`
