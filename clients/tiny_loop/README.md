# Tiny Loop Client Experiment

This is a deliberately small external client for `research-os`.

It is meant to validate one believable loop:
- create a workspace through the HTTP API
- publish two snapshot bundles from outside the control plane
- run a real tiny ML task under a fixed budget
- assert a claim about the better snapshot
- ask the planner what to do next
- follow the recommendation
- fetch human-facing publication output back from the service

## Domain

The task is a tiny synthetic nonlinear regression problem.

- baseline snapshot: linear features
- candidate snapshot: quadratic features
- metric: `val_loss`
- budget: `5` seconds
- platform label: `cpu`

This is intentionally cheap, inspectable, and forkable.

## Profiles

The client has two profiles:
- `eval-sprint`: the default. It targets the canonical seeded effort `Eval Sprint: improve validation loss under fixed budget` after `scripts/seed_demo.py --reset`.
- `inference-sprint`: targets the canonical seeded effort `Inference Sprint: improve flash-path throughput on H100`.
- `standalone`: the original isolated synthetic loop with no seeded effort dependency.

The eval-sprint path is intentionally explicit about being a local proxy contribution. It
joins the canonical seeded effort and uses the tiny synthetic regression task as a cheap
stand-in for the fixed-budget eval contribution shape.

The inference-sprint path does the same for the hardware-aware throughput effort and marks
its events as proxy contributions with a `max` objective direction.

## Run

Start the API first:

```bash
python3 scripts/seed_demo.py --reset
uvicorn apps.api.main:app --reload
```

Then run the client:

```bash
python3 -m clients.tiny_loop.run
```

Or run the isolated standalone profile:

```bash
python3 -m clients.tiny_loop.run --profile standalone
```

Or target the seeded inference effort:

```bash
python3 -m clients.tiny_loop.run --profile inference-sprint
```

To target a hosted shared control plane:

```bash
python3 -m clients.tiny_loop.run --base-url https://api.openintention.io --actor-id <handle>
```

The client prints:
- actor id
- effort name and effort id when it joins a seeded effort
- workspace id
- planner action taken
- reproduced claim id
- discussion markdown
- pull-request markdown

## What this validates

- `research-os` can act as a control plane for a real external loop
- planner output is useful to an outside client
- lineage events can be appended from outside service internals
- publication mirrors can be consumed by humans after the loop finishes
