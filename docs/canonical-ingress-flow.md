# Canonical Ingress Flow

This is the current end-to-end newcomer path for OpenIntention.

It exists to answer one practical question:

> If a person or an AI agent arrives from the public surface with no hidden context, what exact path should they follow first?

This flow is intentionally narrow. It is the launch path we should verify before spending more
time on visuals.

## Who this is for

This flow covers two real entry modes:
- a human newcomer reading the public site and repo
- a human newcomer asking Claude, Codex, or another agent to help them participate

The product should support both.

## End-state definitions

The flow should not stop at "the script ran".

For launch, these terms should mean:

### Onboarded
- the newcomer understands what OpenIntention is
- the newcomer understands what it is not
- the newcomer can identify what is real today versus what is future direction

### Joined
- the newcomer is attached to a specific seeded effort
- a workspace exists for that newcomer inside the effort
- the system can point to that workspace as participation in a shared objective

### Participated
- the newcomer left behind durable research state
- at minimum this should include:
  - a workspace
  - one or more snapshots
  - one or more runs
  - a claim and/or reproduction
  - a visible publication artifact that others can inspect

The launch path should prove all three, not just onboarding.

## Product boundary the newcomer must infer

Before participation, the newcomer should be able to infer:
- OpenIntention is the public brand
- `research-os` is the current technical control-plane implementation
- the control plane, seeded efforts, planner, and publication mirrors are real
- the current tiny-loop client is still a proxy contribution path
- the product is not yet a live mesh or finished community app

If the newcomer cannot infer that from the public surface, the ingress flow is not ready.

## Freshness model

The public surface currently has three different evidence modes:

- live hosted state:
  - `https://openintention.io/efforts`
  - hosted API endpoints and publication mirrors
  - use this for the current shared effort state
- generated snapshot evidence:
  - `data/publications/efforts/*.md`
  - `apps/site/dist/evidence/*.html`
  - refresh with `python3 scripts/export_effort_briefs.py` and `python3 scripts/build_microsite.py`
- deterministic smoke reports:
  - `data/publications/launch/public-ingress/`
  - `data/publications/launch/shared-participation/`
  - `data/publications/launch/nightly-contribution-window-smoke/`
  - `data/publications/launch/overnight-autoresearch-worker-smoke/`
  - use these to prove a path works end to end, not as live counters

## Canonical flow

### Step 1: Arrive from a public surface

Entry points:
- `https://openintention.io`
- `https://github.com/openintention/research-os`
- a public post or message that links those two surfaces

### Step 2: Understand the big picture quickly

The newcomer should be able to answer:
- what problem this product is trying to solve
- what they can do here today
- what is real versus what is future direction

### Step 3: Identify the seeded effort path

The newcomer should find:
- `Eval Sprint: improve validation loss under fixed budget`
- `Inference Sprint: improve flash-path throughput on H100`

The newcomer should understand that these are the current narrow participation surfaces.

### Step 4: Choose the default participation mode

#### Human-first mode

If the newcomer wants the shortest path that actually joins a live seeded effort, they should run:

```bash
curl -fsSL https://openintention.io/join | bash
```

That is the public join command.

If the newcomer wants the shortest deterministic proof of the whole public path, they should run:

```bash
python3 scripts/run_public_ingress_smoke.py
```

This is the canonical "does the public path really work?" verification command.

#### Agent-assisted mode

If the newcomer wants an AI agent to help them participate, they should:
- give the agent `https://openintention.io`
- give the agent `https://github.com/openintention/research-os`
- point the agent to `docs/join-with-ai.md`

The agent should prefer `curl -fsSL https://openintention.io/join | bash` first if it
discovers it.
It should use `python3 scripts/run_public_ingress_smoke.py` as a deterministic fallback.

### Step 5: Complete one narrow participation loop

The expected current loop is:
- discover the repo from the public site
- clone the repo
- run the hosted join bootstrap
- land a visible workspace, claim/reproduction, and report into the live effort state
- generate a local report pointing to the live effort page and workspace discussion

The success condition is not "ran the command". It is:
- onboarded into the product boundary
- joined to a specific effort
- participated by leaving behind durable contribution state

### Step 6: Inspect the resulting evidence

The newcomer should inspect at least one of:
- `data/publications/launch/public-ingress/public-ingress-smoke.md`
- `data/publications/launch/public-ingress/first-user-smoke.md`
- `data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md`
- `data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md`

If the hosted join command was executed, also include:
- `data/publications/launch/hosted-join/hosted-join.md`

The flow is only successful if the newcomer can see concrete artifacts, not just terminal logs.

## Pass criteria

The canonical ingress flow passes if:
- a newcomer can start from the public surface only
- the product boundary is inferred correctly
- the seeded effort path is discovered without hidden context
- the newcomer is onboarded, joined, and participated by the definitions above
- at least one resulting artifact is inspected

## Fail criteria

The canonical ingress flow fails if:
- the newcomer thinks a hosted community app already exists
- the newcomer mistakes proxy loops for production benchmark infrastructure
- the newcomer cannot tell what OpenIntention is versus what `research-os` is
- the newcomer cannot discover how to participate
- the newcomer never becomes attached to a specific effort/workspace
- the newcomer runs commands but leaves behind no durable contribution state
- the newcomer cannot find any inspectable evidence after participation

## Current recommendation

Before launch, the team should verify both:
- a human-first walkthrough
- an agent-assisted walkthrough

The public post should remain blocked until both pass against the current public site and repo.
