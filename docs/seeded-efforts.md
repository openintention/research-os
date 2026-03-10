# First Public Seeded Efforts

These are the first two seeded efforts the system should present publicly.

They are intentionally narrow and legible.

## 1. Eval Sprint: improve validation loss under fixed budget

Type: eval / benchmark improvement

Shape:
- objective: `val_bpb`
- platform: `A100`
- budget: `300` seconds
- contribution pattern: propose or reproduce short model-improvement runs

Why this effort comes first:
- it creates the cleanest collaborative evidence loop
- claims, reproductions, contradictions, and frontier changes are easy to inspect
- contributors can understand what a “good” result looks like quickly

Expected contribution types:
- publish a candidate snapshot
- run it under the fixed budget
- assert or reproduce a claim
- adopt a useful finding into another workspace

Local bootstrap path:
- `python -m clients.tiny_loop.run`
- effort overview mirror: `/api/v1/publications/efforts/<eval_effort_id>`
- exported brief: `data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md`

## 2. Inference Sprint: improve flash-path throughput on H100

Type: inference optimization

Shape:
- objective: `tokens_per_second`
- platform: `H100`
- budget: `300` seconds
- contribution pattern: improve or reproduce throughput on a bounded kernel path

Why this effort comes first:
- it makes hardware-aware participation concrete
- it highlights that frontiers are platform-specific
- it creates a practical reason for multiple contributors with different systems expertise to join

Expected contribution types:
- publish a kernel or runtime-path snapshot
- report throughput runs
- reproduce gains on independent runs
- adopt useful optimizations without merge semantics

Local bootstrap path:
- `python -m clients.tiny_loop.run --profile inference-sprint`
- effort overview mirror: `/api/v1/publications/efforts/<inference_effort_id>`
- exported brief: `data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md`

## Why these two first

Together they express the product correctly:
- eval work proves collaborative evidence and claim quality
- inference work proves hardware-aware contribution and platform-specific frontier value

Other effort classes remain valid later, including tiny autoresearch-style model-improvement
loops, but these two are the best first public shape for the network.
