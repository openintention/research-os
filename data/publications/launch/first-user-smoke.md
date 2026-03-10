# First User Smoke Report

## Base URL
- `http://127.0.0.1:54570`

## Discovered Efforts
- `Inference Sprint: improve flash-path throughput on H100` `tokens_per_second` on `H100` (300s)
- `Eval Sprint: improve validation loss under fixed budget` `val_bpb` on `A100` (300s)

## Eval Client Output
```text
effort_name=Eval Sprint: improve validation loss under fixed budget
effort_id=83383bd4-8700-48a1-83df-6d0e7b8dc190
workspace_id=e47e8598-14b7-4bca-80b8-44542cc119d7
planner_action=reproduce_claim
claim_id=claim-quadratic-001
reproduction_run_id=run-candidate-repro-001

discussion_markdown:
# Discussion: eval-sprint-demo-quadratic

## Workspace
- Objective: `val_bpb`
- Platform: `A100`
- Budget seconds: `300`
- Updated at: `2026-03-10T09:03:34.356487+00:00`
- Description: Local bootstrap participant loop for the seeded eval sprint. It uses the tiny synthetic regression task as a cheap proxy for the fixed-budget contribution shape.

## State
- Snapshots: 2
- Runs: 3
- Claims: 1
- Adoptions: 0
- Summaries: 0
- Events: 8

## Claim Signals
- `claim-quadratic-001` [supported] Adding the quadratic feature improves the seeded eval objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)

## Recent Events
- `claim.reproduced` at 2026-03-10T09:03:34.356487+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-10T09:03:34.354963+00:00 on `run-candidate-repro-001`
- `claim.asserted` at 2026-03-10T09:03:34.350469+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-10T09:03:34.348761+00:00 on `run-candidate-001`
- `run.completed` at 2026-03-10T09:03:34.345735+00:00 on `run-baseline-001`

pull_request_markdown:
# PR: snap-quadratic-candidate

## Context
- Workspace: `eval-sprint-demo-quadratic`
- Objective: `val_bpb`
- Platform: `A100`
- Budget seconds: `300`

## Snapshot
- Snapshot ID: `snap-quadratic-candidate`
- Parent snapshots: none
- Git ref: `refs/experiments/snap-quadratic-candidate`
- Source bundle digest: `sha256:31883c28e66684997e584a3dff013e6c3c556733a20be4ff30518b363c9d35b7`
- Artifact URI: `file:///Users/aliargun/Documents/GitHub/research-os/data/publications/launch/client-artifacts/eval/snap-quadratic-candidate.json`
- Notes: Quadratic feature variant expected to better fit the synthetic data.

## Run Summary
- Best run: `run-candidate-001`
- Metric: `val_bpb` = `0.447392`
- Direction: `min`
- Status: `success`

## Recorded Runs
- `run-candidate-repro-001`: `val_bpb` = `0.491941` (success)
- `run-candidate-001`: `val_bpb` = `0.447392` (success)

## Claim Signals
- `claim-quadratic-001` [supported] Adding the quadratic feature improves the seeded eval objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)
```

## Inference Client Output
```text
effort_name=Inference Sprint: improve flash-path throughput on H100
effort_id=3a4bbc4e-b8b8-4e8d-a65a-fc1a564cdc3c
workspace_id=67ff70ce-8c70-46dd-b524-1dcfb4254dd9
planner_action=reproduce_claim
claim_id=claim-quadratic-001
reproduction_run_id=run-candidate-repro-001

discussion_markdown:
# Discussion: inference-sprint-demo-flash-path

## Workspace
- Objective: `tokens_per_second`
- Platform: `H100`
- Budget seconds: `300`
- Updated at: `2026-03-10T09:03:34.453460+00:00`
- Description: Local bootstrap participant loop for the seeded inference sprint. It uses the tiny synthetic regression task as a cheap proxy for the hardware-aware throughput contribution shape.

## State
- Snapshots: 2
- Runs: 3
- Claims: 1
- Adoptions: 0
- Summaries: 0
- Events: 8

## Claim Signals
- `claim-quadratic-001` [supported] The candidate path improves the seeded inference objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)

## Recent Events
- `claim.reproduced` at 2026-03-10T09:03:34.453460+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-10T09:03:34.452220+00:00 on `run-candidate-repro-001`
- `claim.asserted` at 2026-03-10T09:03:34.447102+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-10T09:03:34.445882+00:00 on `run-candidate-001`
- `run.completed` at 2026-03-10T09:03:34.442902+00:00 on `run-baseline-001`

pull_request_markdown:
# PR: snap-quadratic-candidate

## Context
- Workspace: `inference-sprint-demo-flash-path`
- Objective: `tokens_per_second`
- Platform: `H100`
- Budget seconds: `300`

## Snapshot
- Snapshot ID: `snap-quadratic-candidate`
- Parent snapshots: none
- Git ref: `refs/experiments/snap-quadratic-candidate`
- Source bundle digest: `sha256:a5050f405963901e3f6b394b75277a854000903f4fbd277689da05f6f7bf4824`
- Artifact URI: `file:///Users/aliargun/Documents/GitHub/research-os/data/publications/launch/client-artifacts/inference/snap-quadratic-candidate.json`
- Notes: Quadratic feature variant expected to better fit the synthetic data.

## Run Summary
- Best run: `run-candidate-repro-001`
- Metric: `tokens_per_second` = `0.491941`
- Direction: `max`
- Status: `success`

## Recorded Runs
- `run-candidate-repro-001`: `tokens_per_second` = `0.491941` (success)
- `run-candidate-001`: `tokens_per_second` = `0.447392` (success)

## Claim Signals
- `claim-quadratic-001` [supported] The candidate path improves the seeded inference objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)
```

## Exported Briefs
- `data/publications/launch/effort-briefs/eval-sprint-improve-validation-loss-under-fixed-budget.md`
- `data/publications/launch/effort-briefs/inference-sprint-improve-flash-path-throughput-on-h100.md`
