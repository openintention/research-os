# First User Smoke Report

## Base URL
- `http://127.0.0.1:56854`

## Discovered Efforts
- `Inference Sprint: improve flash-path throughput on H100` `tokens_per_second` on `H100` (300s)
- `Eval Sprint: improve validation loss under fixed budget` `val_bpb` on `A100` (300s)

## Participation Outcome
- Onboarded: the newcomer discovered the public repo and seeded effort path from the public surface.
- Joined (Eval): workspace `977d23eb-e87a-42dc-af47-38863916ad2d` attached to effort `Eval Sprint: improve validation loss under fixed budget`.
- Joined (Inference): workspace `f7aa4fe2-eba6-4cf6-a023-06d6eeb6488a` attached to effort `Inference Sprint: improve flash-path throughput on H100`.
- Participated (Eval): workspace `977d23eb-e87a-42dc-af47-38863916ad2d` left behind claim `977d23eb-claim-quadratic-001` and reproduction run `977d23eb-run-candidate-repro-001`.
- Participated (Inference): workspace `f7aa4fe2-eba6-4cf6-a023-06d6eeb6488a` left behind claim `f7aa4fe2-claim-quadratic-001` and reproduction run `f7aa4fe2-run-candidate-repro-001`.

## Eval Client Output
```text
actor_id=participant-4f250f8d
participant_role=contributor
effort_name=Eval Sprint: improve validation loss under fixed budget
effort_id=c9c0c376-a123-450c-9298-897603acb74f
workspace_id=977d23eb-e87a-42dc-af47-38863916ad2d
planner_action=reproduce_claim
claim_id=977d23eb-claim-quadratic-001
reproduction_run_id=977d23eb-run-candidate-repro-001

discussion_markdown:
# Discussion: eval-sprint-demo-quadratic

## Workspace
- Started by: `participant-4f250f8d`
- Role: `contributor`
- Objective: `val_bpb`
- Platform: `A100`
- Budget seconds: `300`
- Updated at: `2026-03-12T23:43:27.810758+00:00`
- Description: Local bootstrap participant loop for the seeded eval sprint. It uses the tiny synthetic regression task as a cheap proxy for the fixed-budget contribution shape.

## State
- Snapshots: 2
- Runs: 3
- Claims: 1
- Reproductions: 1
- Adoptions: 0
- Summaries: 0
- Events: 8

## Claim Signals
- `977d23eb-claim-quadratic-001` [supported] Adding the quadratic feature improves the seeded eval objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)

## Recent Events
- `claim.reproduced` at 2026-03-12T23:43:27.810758+00:00 on `977d23eb-claim-quadratic-001`
- `run.completed` at 2026-03-12T23:43:27.809038+00:00 on `977d23eb-run-candidate-repro-001`
- `claim.asserted` at 2026-03-12T23:43:27.804804+00:00 on `977d23eb-claim-quadratic-001`
- `run.completed` at 2026-03-12T23:43:27.803481+00:00 on `977d23eb-run-candidate-001`
- `run.completed` at 2026-03-12T23:43:27.800202+00:00 on `977d23eb-run-baseline-001`

pull_request_markdown:
# PR: 977d23eb-snap-quadratic-candidate

## Context
- Workspace: `eval-sprint-demo-quadratic`
- Objective: `val_bpb`
- Platform: `A100`
- Budget seconds: `300`

## Snapshot
- Snapshot ID: `977d23eb-snap-quadratic-candidate`
- Parent snapshots: none
- Git ref: `refs/experiments/977d23eb-snap-quadratic-candidate`
- Source bundle digest: `sha256:f9716e73685ef169416dec1ab90fdd562748cdcc546cd9b9642063dac8ac1e2b`
- Artifact reference: `local artifact plane path hidden (digest=sha256:f9716e73685ef169416dec1ab90fdd562748cdcc546cd9b9642063dac8ac1e2b)`
- Notes: Quadratic feature variant expected to better fit the synthetic data.

## Run Summary
- Best run: `977d23eb-run-candidate-001`
- Metric: `val_bpb` = `0.447392`
- Direction: `min`
- Status: `success`

## Recorded Runs
- `977d23eb-run-candidate-repro-001`: `val_bpb` = `0.491941` (success)
- `977d23eb-run-candidate-001`: `val_bpb` = `0.447392` (success)

## Claim Signals
- `977d23eb-claim-quadratic-001` [supported] Adding the quadratic feature improves the seeded eval objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)
```

## Inference Client Output
```text
actor_id=participant-f87d4237
participant_role=contributor
effort_name=Inference Sprint: improve flash-path throughput on H100
effort_id=e5438af2-48a0-48cd-9d86-f1afa9125fe1
workspace_id=f7aa4fe2-eba6-4cf6-a023-06d6eeb6488a
planner_action=reproduce_claim
claim_id=f7aa4fe2-claim-quadratic-001
reproduction_run_id=f7aa4fe2-run-candidate-repro-001

discussion_markdown:
# Discussion: inference-sprint-demo-flash-path

## Workspace
- Started by: `participant-f87d4237`
- Role: `contributor`
- Objective: `tokens_per_second`
- Platform: `H100`
- Budget seconds: `300`
- Updated at: `2026-03-12T23:43:27.965428+00:00`
- Description: Local bootstrap participant loop for the seeded inference sprint. It uses the tiny synthetic regression task as a cheap proxy for the hardware-aware throughput contribution shape.

## State
- Snapshots: 2
- Runs: 3
- Claims: 1
- Reproductions: 1
- Adoptions: 0
- Summaries: 0
- Events: 8

## Claim Signals
- `f7aa4fe2-claim-quadratic-001` [supported] The candidate path improves the seeded inference objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)

## Recent Events
- `claim.reproduced` at 2026-03-12T23:43:27.965428+00:00 on `f7aa4fe2-claim-quadratic-001`
- `run.completed` at 2026-03-12T23:43:27.964049+00:00 on `f7aa4fe2-run-candidate-repro-001`
- `claim.asserted` at 2026-03-12T23:43:27.959597+00:00 on `f7aa4fe2-claim-quadratic-001`
- `run.completed` at 2026-03-12T23:43:27.958404+00:00 on `f7aa4fe2-run-candidate-001`
- `run.completed` at 2026-03-12T23:43:27.955661+00:00 on `f7aa4fe2-run-baseline-001`

pull_request_markdown:
# PR: f7aa4fe2-snap-quadratic-candidate

## Context
- Workspace: `inference-sprint-demo-flash-path`
- Objective: `tokens_per_second`
- Platform: `H100`
- Budget seconds: `300`

## Snapshot
- Snapshot ID: `f7aa4fe2-snap-quadratic-candidate`
- Parent snapshots: none
- Git ref: `refs/experiments/f7aa4fe2-snap-quadratic-candidate`
- Source bundle digest: `sha256:b950cd699fd070bb78d85e7654e0025c944c8ed87f1a286a49ed985cbf7058a8`
- Artifact reference: `local artifact plane path hidden (digest=sha256:b950cd699fd070bb78d85e7654e0025c944c8ed87f1a286a49ed985cbf7058a8)`
- Notes: Quadratic feature variant expected to better fit the synthetic data.

## Run Summary
- Best run: `f7aa4fe2-run-candidate-repro-001`
- Metric: `tokens_per_second` = `0.491941`
- Direction: `max`
- Status: `success`

## Recorded Runs
- `f7aa4fe2-run-candidate-repro-001`: `tokens_per_second` = `0.491941` (success)
- `f7aa4fe2-run-candidate-001`: `tokens_per_second` = `0.447392` (success)

## Claim Signals
- `f7aa4fe2-claim-quadratic-001` [supported] The candidate path improves the seeded inference objective in this local proxy loop under the fixed budget. (support=1, contradictions=0)
```

## Exported Briefs
- `/var/folders/md/v28l21z50lj6nq4f18p501hr0000gn/T/openintention-public-ingress-9p70_p_z/first-user/effort-briefs/eval-sprint-improve-validation-loss-under-fixed-budget.md`
- `/var/folders/md/v28l21z50lj6nq4f18p501hr0000gn/T/openintention-public-ingress-9p70_p_z/first-user/effort-briefs/inference-sprint-improve-flash-path-throughput-on-h100.md`
