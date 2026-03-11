# First User Smoke Report

## Base URL
- `http://127.0.0.1:52582`

## Discovered Efforts
- `Inference Sprint: improve flash-path throughput on H100` `tokens_per_second` on `H100` (300s)
- `Eval Sprint: improve validation loss under fixed budget` `val_bpb` on `A100` (300s)

## Eval Client Output
```text
effort_name=Eval Sprint: improve validation loss under fixed budget
effort_id=411310cd-cde5-41f9-bebf-1473cab80c9a
workspace_id=456f96ad-caa2-4494-ba71-2bc16c271f9a
planner_action=reproduce_claim
claim_id=claim-quadratic-001
reproduction_run_id=run-candidate-repro-001

discussion_markdown:
# Discussion: eval-sprint-demo-quadratic

## Workspace
- Objective: `val_bpb`
- Platform: `A100`
- Budget seconds: `300`
- Updated at: `2026-03-11T09:07:36.470159+00:00`
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
- `claim.reproduced` at 2026-03-11T09:07:36.470159+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-11T09:07:36.467565+00:00 on `run-candidate-repro-001`
- `claim.asserted` at 2026-03-11T09:07:36.460729+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-11T09:07:36.457933+00:00 on `run-candidate-001`
- `run.completed` at 2026-03-11T09:07:36.453487+00:00 on `run-baseline-001`

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
effort_id=4c709987-ec7c-41e9-b869-654115280dba
workspace_id=9af57f9e-90ed-45b6-b265-1539b6e85530
planner_action=reproduce_claim
claim_id=claim-quadratic-001
reproduction_run_id=run-candidate-repro-001

discussion_markdown:
# Discussion: inference-sprint-demo-flash-path

## Workspace
- Objective: `tokens_per_second`
- Platform: `H100`
- Budget seconds: `300`
- Updated at: `2026-03-11T09:07:36.609240+00:00`
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
- `claim.reproduced` at 2026-03-11T09:07:36.609240+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-11T09:07:36.606207+00:00 on `run-candidate-repro-001`
- `claim.asserted` at 2026-03-11T09:07:36.599652+00:00 on `claim-quadratic-001`
- `run.completed` at 2026-03-11T09:07:36.596154+00:00 on `run-candidate-001`
- `run.completed` at 2026-03-11T09:07:36.591673+00:00 on `run-baseline-001`

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
- `/var/folders/md/v28l21z50lj6nq4f18p501hr0000gn/T/openintention-public-ingress-_9ts0831/first-user/effort-briefs/eval-sprint-improve-validation-loss-under-fixed-budget.md`
- `/var/folders/md/v28l21z50lj6nq4f18p501hr0000gn/T/openintention-public-ingress-_9ts0831/first-user/effort-briefs/inference-sprint-improve-flash-path-throughput-on-h100.md`
