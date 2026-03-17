# Goal-To-Effort Translation

## Why this note exists

OpenIntention should read as a goal-and-contribution product on the public surface.

The current `research-os` domain model, API, and route layout still use `Effort` as the runtime
object that anchors shared work.

This note makes that translation explicit so the product language and the machine contract stay
aligned instead of drifting apart.

## Current rule

Use `goal` as the primary public-facing noun.

Use `effort` when you are talking about:
- the current domain object
- API payloads and routes
- event-log semantics
- projection and storage internals

## Current translation

- public goal -> current `EffortView`
- goal page -> `/efforts/<effort_id>`
- seeded goal -> seeded effort in the control plane
- join a goal -> join the effort that currently represents that goal
- goal progress -> workspace, run, claim, reproduction, adoption, frontier, and publication state

## Why we are not adding a first-class Goal object yet

The current public product still starts from seeded goals and one active effort window per goal.

We do not need a first-class `Goal` domain object until one or more of these becomes true:
- users can define their own goals directly through the public product
- one goal needs multiple active efforts at the same time
- goal revisions need their own typed history separate from effort history
- subscriptions, notifications, or planning need a stable goal identity above effort rollovers

Until then, the right move is:
- keep the runtime contract stable
- translate it clearly on the public surface
- avoid pretending the product already exposes user-authored goal creation if it does not

## Product implication

Today the honest story is:
- OpenIntention helps people join seeded ML goals
- those goals are implemented as effort objects in the current control plane
- the work becomes visible through goal pages backed by live effort state

Later, if user-defined goals become core to the product, we should revisit whether `Goal` becomes
first-class in the domain model.
