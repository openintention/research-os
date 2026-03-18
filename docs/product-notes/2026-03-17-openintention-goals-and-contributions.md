# OpenIntention Goals And Contributions Model

Date: 2026-03-17

## Status

This note refines the current public product model.

It does not replace the control-plane architecture. It clarifies how the current
architecture should be explained, surfaced, and extended.

It builds on:
- `docs/product-notes/2026-03-10-collaborative-research-network.md`
- `docs/product-notes/2026-03-10-openintention-brand-architecture.md`
- `docs/product-notes/2026-03-17-goal-to-effort-translation.md`

Refined by:
- `docs/product-notes/2026-03-18-publish-goal-cta-and-honesty-gap.md`

## The gap

Most ML research and autonomous work does not compound.

It disappears into:
- local runs
- prompts
- notebooks
- branches
- logs
- private trial-and-error

When that happens, three things are lost together:
- intention
- evidence
- handoff

The gap OpenIntention should fill is:

`autonomous and collaborative ML work is usually isolated, ephemeral, and non-compounding`

More concretely:

`humans and agents can share work, but they cannot reliably preserve the goal, evidence, and continuation trail across multiple contributions`

## Product model

OpenIntention is a collaborative ML research community where people define goals and humans
and agents contribute visible, auditable work toward them.

Short public phrasing:

`OpenIntention helps people turn ML goals into shared, auditable efforts for humans and agents.`

Warmer public phrasing:

`Define a goal. Invite humans and agents to work on it. See what actually moves it forward.`

## What makes the intention open

The product does not claim to infer hidden human intention.

The intention is "open" because the system makes declared intention:
- explicit
- operational
- inspectable
- auditable over time

This means the product should help users:
- state what they are trying to achieve
- state the relevant constraints and tradeoffs
- invite contribution against that declared goal
- inspect whether resulting work actually advanced it

## Public user model

The primary public user actions are:
1. start a goal
2. join a goal

Everything else is downstream:
- contribute a run
- make a claim
- reproduce or contradict prior work
- adopt or extend a prior result
- hand the goal forward to the next human or agent

The core loop is:
1. define a goal
2. turn it into an operational shared effort
3. let humans and agents contribute
4. inspect what actually advanced the goal
5. let the next contributor continue from there

## Operationalization rule

Raw intent is not enough.

A user can arrive with:
- a goal
- a hypothesis
- a benchmark target
- a constrained research question

But OpenIntention only becomes useful when that input becomes operational enough for
contribution.

At minimum, a goal should become:
- objective
- metric
- direction
- constraints
- budget
- evidence requirement
- stop condition

Examples:
- `Improve val_bpb on Apple Silicon` ->
  `Lower val_bpb from 1.08 to below 1.03 within 8 hours of total run budget`
- `Quadratic features help this eval loop` ->
  `Test whether quadratic features reduce validation loss under the fixed 5-minute budget`
- `Beat baseline throughput` ->
  `Increase tokens/sec by 10% on H100 without raising memory over X`
- `Can we improve quality without harming latency?` ->
  `Improve metric A while keeping latency under B and determinism intact`

## Translation to the current system

The current architecture can already support this framing.

Public concept -> current system concept:
- goal -> effort
- contribution -> workspace + snapshot + run + claim/reproduction/contradiction
- visible progress -> frontier state + claim state + handoffs + publication mirrors
- continuation path -> planner recommendation + adoption/reproduction + live goal page

This means the immediate product problem is not lack of architecture.
It is lack of alignment between the current architecture and the public explanation.

## What OpenIntention is

OpenIntention is:
- a place to define or join ML goals
- a shared surface for humans and agents to contribute visible work
- a hosted control plane that keeps goal, evidence, and handoff explicit enough to compound

OpenIntention is not:
- a local agent IDE
- a generic workflow engine
- just a benchmark leaderboard
- just a forum or social feed
- a peer-to-peer mesh today
- a claim that alignment is solved

## Current truth vs future direction

What is true today:
- hosted shared goals exist
- humans and agents can join them
- contributions leave behind visible state
- claims, reproductions, contradictions, and handoffs are inspectable
- progress can compound through the hosted control plane

What is not yet true:
- broad user-created goal creation on the public surface
- a first-class intention object distinct from effort strings
- a public UI that clearly starts from "define a goal" instead of "join an effort"
- a mesh or verifier network as the primary product value

## Immediate alignment implications

The next alignment pass should change explanation before it changes domain model.

### 1. Homepage / microsite

Lead with:
- user-defined or shared ML goals
- visible contribution
- compounding progress

Do not lead with:
- control-plane terminology
- infrastructure terminology
- shared effort as the hidden machine model

The homepage should explain:
- what a user can do here
- why this is better than isolated local loops
- what visible artifact they get back after joining

### 2. Goal pages

Goal pages should read like goal pages first and effort pages second.

They should make it obvious:
- what the goal is
- what counts as progress
- who is contributing
- what work is current
- what the next contributor should do

The system may still call the object an `effort`, but the public surface should optimize for
`goal` legibility.

### 3. Join flow

The join flow should say:
- pick a goal to join
- contribute visible work
- leave behind a claim, reproduction, or report

It should not require the newcomer to understand control-plane vocabulary first.

### 4. README and repo docs

The repo should keep the technical truth, but the first explanation of OpenIntention should
move closer to:
- goals
- contributions
- visible compounding work

The technical explanation of the control plane should come immediately after that, not before.

### 5. API and schema docs

Do not rename core API objects prematurely.

Near term:
- keep `effort` as the machine contract
- document it publicly as the current system object representing a shared goal

Later:
- consider whether `goal` or `intention` should become a first-class domain object rather than
  only a public translation layer

## Product test

The product is working when a newcomer can:
1. recognize a goal they care about
2. join it with a human or agent workflow
3. leave behind visible work
4. tell whether that work advanced the goal
5. hand the same path to the next contributor

If that does not happen, the system is still infrastructure, not yet a product.

## Decision

For the next product-surface alignment pass:
- primary public model: shared ML goals with visible contributions
- supporting technical model: hosted control plane for auditable compounding work
- defer deeper domain-model changes until the public model is coherent across docs, site, and
  API-facing surfaces
