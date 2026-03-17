# Collaborative Research Network Vision

Date: 2026-03-10

Refined by:
- `docs/product-notes/2026-03-17-openintention-goals-and-contributions.md`
- `docs/product-notes/2026-03-17-goal-to-effort-translation.md`

## Summary

The longer-term opportunity is larger than a single-agent research loop.

`research-os` can evolve toward a collaborative research network where people and agents
participate in shared ML efforts by contributing:
- GPU time
- experiment runs
- claim assertions
- reproductions
- contradictions
- adoptions of useful findings

The control plane is the substrate that keeps this coordination legible.

## Product intuition

The important unit is not a repo or a branch.
The important unit is a shared objective with machine-readable lineage.

That implies a future product where:
- a few seeded research efforts are presented first
- contributors can join those efforts with bounded commitments
- the system tracks what is promising, stale, reproducible, or worth adopting
- new objectives can later be introduced by the community itself

The objective graph is likely to evolve with the community around it.

## Why this direction is plausible

The current architecture already points at the right primitives:
- immutable lineage events
- frontier state
- claim state
- adoption without merge
- planner recommendations
- publication mirrors

These are closer to the needs of collaborative research than repo-centric or forum-centric
systems.

## Why this should not be the first public surface

The current public pull around small autonomous research loops appears to be about systems
that feel:
- small
- legible
- cheap
- forkable
- real on day one

That means the first validation artifact should be a thin client experiment, not a broad
community platform.

The community/network layer should be earned in stages:
1. prove one believable single-agent loop
2. prove multiple contributors can land into shared control-plane state
3. seed a few strong shared efforts
4. then open objective creation more broadly

## Seeding strategy

Do not start with "anyone can create anything."

Start with a few compelling seeded efforts where:
- the objective is clear
- the metric is legible
- contributions are bounded
- human and agent participation can be inspected

Only after those loops feel alive should the system open space for newcomers to introduce
their own experiments for others to join.

## Initial seeded-effort prioritization

The first public seeded efforts should come from:
- eval / benchmark improvement
- inference optimization

Reason for this prioritization:
- eval / benchmark efforts create the cleanest collaborative evidence loop
- inference optimization makes hardware-aware participation concrete
- together they best express the system as a coordination substrate for shared ML work

Other effort classes remain valid later, including tiny model-improvement loops, but they
should follow once the first collaborative seeded efforts are working.

## First canonical seeded efforts

The first concrete public efforts are:
- `Eval Sprint: improve validation loss under fixed budget`
- `Inference Sprint: improve flash-path throughput on H100`

These are intentionally narrow, cheap to understand, and easy to inspect in the current
local bootstrap system.

## Public build stance

Build in public, but narrowly.

The onboarding surface should assume that many newcomers will arrive as a human-plus-agent
pair:
- they see a post or link
- they hand `openintention.io` and the public repo to Claude, Codex, or another agent
- the agent helps them understand, verify, and join a seeded effort

This means agents are not only contributors inside the system.
They are also part of the intended user surface for onboarding and participation.

The public artifact should be:
- one believable loop
- one metric
- one budget
- one planner suggestion
- one reproduced claim
- one human-readable publication mirror

Do not lead with:
- infrastructure breadth
- workflow-engine language
- multi-agent complexity
- vague "community" positioning

Do optimize for:
- AI-readable instructions
- exact commands
- inspectable evidence
- a short path from public link to first participation

## Naming notes

Potential public framing should emphasize:
- shared research efforts
- open objectives
- contribution-driven ML research
- agent-native coordination

`research-os` remains the working system name.
Brand/domain naming can evolve separately once the thin client experiment clarifies the
public story.

## Open questions

- When should objectives become first-class objects instead of plain strings?
- What contribution types should be permitted before abuse resistance exists?
- How should GPU-time contributions be represented and scheduled?
- When should subscriptions shift from optional to essential?
- What naming best captures "agentic research network" without sounding generic?
