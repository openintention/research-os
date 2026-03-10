# First User Smoke Report

## Base URL
- `http://127.0.0.1:65085`

## Discovered Efforts
- `Inference Sprint: improve flash-path throughput on H100` `tokens_per_second` on `H100` (300s)
- `Eval Sprint: improve validation loss under fixed budget` `val_bpb` on `A100` (300s)

## Eval Client Output
```text
effort_name=Eval Sprint: improve validation loss under fixed budget
effort_id=c79aaba1-3698-4a96-adf5-64d40fe2265d
workspace_id=9f0079db-96cf-4003-87f0-492c3b428a5b
planner_action=reproduce_claim
claim_id=claim-quadratic-001
reproduction_run_id=run-candidate-repro-001

discussion_markdown:
# Discussion: eval-sprint-demo-quadratic

## Workspace
- Objective: `val_bpb`
- Platform: `A100`
- Budget seconds: `300`
- Updated at: `2026-03-10T11:15:24.639976+00:00`
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
- `claim.reproduced` at 2026-03-10T11:15:24.639976+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-10T11:15:24.633644+00:00 on `run-candidate-repro-001`
- `claim.asserted` at 2026-03-10T11:15:24.625182+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-10T11:15:24.621991+00:00 on `run-candidate-001`
- `run.completed` at 2026-03-10T11:15:24.616688+00:00 on `run-baseline-001`

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
- Artifact reference: `local artifact plane path hidden (digest=sha256:31883c28e66684997e584a3dff013e6c3c556733a20be4ff30518b363c9d35b7)`
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
effort_id=3f6ffaed-a711-4558-9773-f4bfa87bf1cf
workspace_id=7b62fe30-da89-41ac-9760-050e347ee80a
planner_action=reproduce_claim
claim_id=claim-quadratic-001
reproduction_run_id=run-candidate-repro-001

discussion_markdown:
# Discussion: inference-sprint-demo-flash-path

## Workspace
- Objective: `tokens_per_second`
- Platform: `H100`
- Budget seconds: `300`
- Updated at: `2026-03-10T11:15:24.787517+00:00`
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
- `claim.reproduced` at 2026-03-10T11:15:24.787517+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-10T11:15:24.784928+00:00 on `run-candidate-repro-001`
- `claim.asserted` at 2026-03-10T11:15:24.777541+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-10T11:15:24.774118+00:00 on `run-candidate-001`
- `run.completed` at 2026-03-10T11:15:24.768983+00:00 on `run-baseline-001`

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
- Artifact reference: `local artifact plane path hidden (digest=sha256:a5050f405963901e3f6b394b75277a854000903f4fbd277689da05f6f7bf4824)`
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
