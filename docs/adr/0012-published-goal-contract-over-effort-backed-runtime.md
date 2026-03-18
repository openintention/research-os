# ADR 0012: Published Goal Contract Over Effort-Backed Runtime

## Status

Accepted

## Context

OpenIntention's public model is goal-first:
- people join shared ML goals
- humans and agents leave visible work behind
- the next contributor should be able to continue from that work

The current control plane runtime is still effort-backed:
- goal page route: `/efforts/{effort_id}`
- shared state attaches to `EffortView`
- workspace, claim, frontier, and publication projections already key off effort scope

We now need a self-serve v1 path for public goal creation without destabilizing the current event
log, projection model, or seeded-goal onboarding.

## Decision

Add a public published-goal contract above the existing effort runtime.

In v1:
- the user-facing noun stays `goal`
- the runtime object remains `effort`
- published goals are created through `POST /api/v1/goals/publish`
- publish requests are normalized into `effort.registered` events with an attached goal contract
- the goal contract is rendered on the live goal page and the markdown publication mirror

The v1 goal contract includes:
- title
- summary
- objective
- metric name
- direction
- platform
- budget seconds
- constraints
- evidence requirement
- stop condition
- author handle

Published goals are tagged with:
- `goal_origin=user-published`
- `join_mode=tiny-loop-proxy`
- `published=true`

## Consequences

Positive:
- OpenIntention can honestly offer a self-serve publish path without replacing the effort-backed
  runtime
- published goals become joinable immediately through the existing contribution flow
- the goal contract becomes visible on live goal pages and publication mirrors
- the public model gets closer to "publish a goal and invite others to join" without overclaiming
  a broader community surface

Negative:
- `goal` remains a public abstraction over `effort`, which means naming translation still has to
  stay explicit in docs and UI
- user-authored goal attribution is still only lightweight asserted handle in v1
- the contribution path for published goals still uses the tiny-loop proxy rather than a richer
  research harness
- public goal creation increases moderation and spam-surface pressure that v1 only addresses with
  lightweight validation and operator review

## Rejected Alternatives

### Make `Goal` a new first-class aggregate immediately

Rejected for v1 because it would duplicate the already-working effort-backed runtime and require a
larger projection/API rewrite before we had validated that public goal creation actually matters.

### Keep goal publishing as a manual operator-only process

Rejected because it blocks the product direction we want to validate:
- can someone publish a goal
- invite another participant in
- and see visible work compound around that published goal

## Verification Expectation

Changes to the published-goal path are not done until they pass:
- deterministic tests for publish validation and rendering
- a publish-goal smoke that proves publish -> follow-on join -> live goal page
- production verification for the affected public surface before the issue is closed
