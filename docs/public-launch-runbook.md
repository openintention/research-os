# Public Launch Runbook

This is the current narrow public-build flow for seeded efforts.

Use it to produce artifacts that are honest, inspectable, and derived from machine state.

## Goal

Show one believable loop around shared efforts without overclaiming what the system already
proves.

Current seeded efforts:
- `Eval Sprint: improve validation loss under fixed budget`
- `Inference Sprint: improve flash-path throughput on H100`

## Operator flow

Verify the actual public ingress path first:

```bash
python3 scripts/run_public_ingress_smoke.py
```

That command starts from `https://openintention.io`, discovers the public repo, clones it,
and runs the canonical seeded-effort smoke flow through a fresh local checkout. The durable
report lands under `data/publications/launch/public-ingress/`.

Seed the current local state:

```bash
python3 scripts/seed_demo.py --reset
```

Run the canonical eval proxy contribution:

```bash
python3 -m clients.tiny_loop.run
```

Run the canonical inference proxy contribution:

```bash
python3 -m clients.tiny_loop.run --profile inference-sprint
```

Export the effort briefs:

```bash
python3 scripts/export_effort_briefs.py
# or
make export-effort-briefs
```

The exported markdown files land in:
- `data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md`
- `data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md`

## What to share publicly

Share:
- the seeded effort brief markdown
- one client run snippet showing the effort name, workspace id, and planner action
- one publication mirror excerpt
- one sentence on why the effort is interesting to join

Do not lead with:
- architecture diagrams
- generic agent-platform language
- broad claims about community features that do not exist yet

## Honesty line

Be explicit about the current proxy contribution loops:
- the seeded effort join flows are real
- the event log, planner, projections, and publication mirrors are real
- the tiny-loop client is a local proxy contribution path
- the current proxy runs are not the same thing as real A100 or H100 benchmarking evidence

This distinction should appear anywhere the current client experiment is shown publicly.

## Recommended public post shape

Use a short post structure:
1. one sentence on the effort
2. one sentence on the contribution loop
3. one artifact excerpt or screenshot from the exported brief
4. one exact command someone can run locally
5. one sentence on what is real today versus what is still proxy behavior

Recommended anchor:
- publish a founder post in Ali's own voice first
- then use a shorter reply or quote-reply on the Andrej Karpathy post that frames the
  collaborative-agent research problem directly
- position `OpenIntention` as the public umbrella and `research-os` as the technical control
  plane underneath it

## Message discipline

Prefer:
- shared effort
- joinable loop
- machine-native research control plane
- publication mirror derived from state

Avoid:
- “community platform” as the headline
- “multi-agent network” as the headline
- implying that current proxy loops are production-grade benchmark infrastructure
